# 強化学習による自動売買アルゴリズム（PPO/SAC対応）
# 必要なライブラリ: stable-baselines3, gymnasium, numpy, pandas
import os
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
# from stable_baselines3 import SAC  # SACを使いたい場合はこちら
from stable_baselines3.common.callbacks import BaseCallback
import matplotlib.pyplot as plt

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# 出力ディレクトリの設定
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')
# 入力ディレクトリの設定
S_INPUT_DIR = os.path.join(S_FILE_DIR, 'input')

# --- 環境クラス定義 ---


class TradingEnv(gym.Env):
    def __init__(self, df: pd.DataFrame, initial_balance=1_000_000, n_history=3000):
        super().__init__()
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.n_history = n_history
        self.action_space = spaces.Discrete(3)  # 0:何もしない, 1:買い, 2:売り
        n_price_bins = self.n_history
        n_candle = self.n_history * 4
        obs_dim = n_price_bins + 9 + n_candle + 1  # PER/PBR削除、短期指標4種追加
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)
        # データ数がn_history未満の場合はエラー
        if len(self.df) <= self.n_history:
            raise ValueError(f"データ数が{self.n_history}未満です: {len(self.df)} 行")
        self.reset()

    def reset(self, seed=None, options=None):
        self.balance = self.initial_balance
        self.position = 0  # 0:ノーポジ, 1:買い
        self.entry_price = None
        # エピソードごとに1日分のデータ範囲を選択
        if not hasattr(self, 'unique_dates'):
            self.unique_dates = self.df['日付'].unique()
            self.episode_idx = -1
        self.episode_idx = (self.episode_idx + 1) % len(self.unique_dates)
        self.episode_date = self.unique_dates[self.episode_idx]
        # この日のインデックス範囲を特定
        self.episode_indices = self.df[self.df['日付'] == self.episode_date].index.tolist()
        self.episode_start = self.episode_indices[0]
        self.episode_end = self.episode_indices[-1]
        self.current_step = self.episode_start
        self.done = False
        return self._get_obs(), {}

    def _normalize(self, x, mean, std, eps=1e-8):
        return (x - mean) / (std + eps)

    def _get_obs(self):
        # current_stepが範囲外の場合はゼロ埋め
        if self.current_step < self.n_history:
            # データが足りない場合はゼロ埋め
            volume_by_price = np.zeros(self.n_history)
            candle = np.zeros(self.n_history * 4)
            now = {k: 0.0 for k in ['終値','MACD','シグナルライン','前日終値','始値','RSI','MA乖離率','出来高比','ボラティリティ']}
        else:
            volume_by_price = self.df['出来高'].iloc[self.current_step - self.n_history:self.current_step].values
            candle = self.df[['始値', '高値', '安値', '終値']].iloc[self.current_step-self.n_history:self.current_step].values.flatten()
            now = self.df.iloc[self.current_step]
        # 特徴量の正規化
        # 終値・始値・高値・安値・MACD・シグナルライン・前日終値・RSI・MA乖離率・出来高比・ボラティリティ
        price_cols = ['終値','始値','高値','安値','MACD','シグナルライン','前日終値']
        price_means = self.df[price_cols].mean()
        price_stds = self.df[price_cols].std()
        norm_now = {}
        for col in price_cols:
            norm_now[col] = self._normalize(now.get(col, 0.0) if isinstance(now, pd.Series) else 0.0, price_means[col], price_stds[col])
        # RSI, MA乖離率, 出来高比, ボラティリティ
        norm_now['RSI'] = self._normalize(now.get('RSI', 0.0) if isinstance(now, pd.Series) else 0.0, 50, 25)
        norm_now['MA乖離率'] = self._normalize(now.get('MA乖離率', 0.0) if isinstance(now, pd.Series) else 0.0, 0, 0.05)
        norm_now['出来高比'] = self._normalize(now.get('出来高比', 0.0) if isinstance(now, pd.Series) else 0.0, 1, 0.5)
        norm_now['ボラティリティ'] = self._normalize(now.get('ボラティリティ', 0.0) if isinstance(now, pd.Series) else 0.0, 0, 50)
        # volume_by_price, candleも正規化
        vol_mean = self.df['出来高'].mean()
        vol_std = self.df['出来高'].std()
        volume_by_price = self._normalize(volume_by_price, vol_mean, vol_std)
        candle_mean = self.df[['始値','高値','安値','終値']].values.mean()
        candle_std = self.df[['始値','高値','安値','終値']].values.std()
        candle = self._normalize(candle, candle_mean, candle_std)
        obs = np.concatenate([
            volume_by_price,
            [norm_now['終値'], norm_now['MACD'], norm_now['シグナルライン'], norm_now['前日終値'], norm_now['始値'], norm_now['RSI'], norm_now['MA乖離率'], norm_now['出来高比'], norm_now['ボラティリティ']],
            candle,
            [self.position]
        ])
        # NaNやinfを0に置換
        obs = np.nan_to_num(obs, nan=0.0, posinf=0.0, neginf=0.0)
        return obs.astype(np.float32)

    def step(self, action):
        reward = 0
        prev_price = self.df.iloc[self.current_step]['終値']
        self.current_step += 1
        # 範囲外参照防止
        if self.current_step >= len(self.df):
            self.done = True
            self.current_step = len(self.df) - 1
        today = self.df.iloc[self.current_step]['日付'] if self.current_step < len(self.df) else None
        prev_day = self.df.iloc[self.current_step - 1]['日付'] if self.current_step - 1 < len(self.df) else None
        now_price = self.df.iloc[self.current_step]['終値'] if self.current_step < len(self.df) else prev_price
        force_sell = False
        trade_cost = 0.001  # 取引コスト（例: 0.1%）
        # ポジションがある場合のみ決済（売り or 日付変更 or 終了）
        if self.position == 1:
            if action == 2 or today != prev_day or self.done:
                gross_profit = now_price - self.entry_price
                cost = (self.entry_price + now_price) * trade_cost
                reward = gross_profit - cost
                self.position = 0
                self.entry_price = None
                force_sell = True
        # 買いはノーポジ時のみ
        if action == 1 and self.position == 0 and not force_sell:
            self.position = 1
            self.entry_price = now_price
            # 買い時にもコストを課す
            reward -= now_price * trade_cost
        return self._get_obs(), reward, self.done, False, {}

class RewardLoggerCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        self.current_rewards = 0
        self.current_length = 0

    def _on_step(self) -> bool:
        reward = self.locals.get('rewards', [0])[0]
        done = self.locals.get('dones', [False])[0]
        self.current_rewards += reward
        self.current_length += 1
        if done:
            self.episode_rewards.append(self.current_rewards)
            self.episode_lengths.append(self.current_length)
            self.current_rewards = 0
            self.current_length = 0
        return True

def plot_learning_curve(rewards, lengths):
    plt.figure(figsize=(10, 5))
    plt.plot(rewards, label='Episode Reward')
    plt.xlabel('Episode')
    plt.ylabel('Reward')
    plt.title('Learning Curve')
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()

def plot_trade_history(df, trade_history):
    plt.figure(figsize=(14, 8))
    ax1 = plt.subplot(2, 1, 1)
    plt.plot(df['日時'], df['終値'], label='Close Price', color='black')
    buy_steps = [h['step'] for h in trade_history if h['action'] == 1]
    sell_steps = [h['step'] for h in trade_history if h['action'] == 2]
    buy_prices = [h['price'] for h in trade_history if h['action'] == 1]
    sell_prices = [h['price'] for h in trade_history if h['action'] == 2]
    plt.scatter(df['日時'].iloc[buy_steps], buy_prices, marker='^', color='green', label='Buy', s=80)
    plt.scatter(df['日時'].iloc[sell_steps], sell_prices, marker='v', color='red', label='Sell', s=80)
    plt.xlabel('Datetime')
    plt.ylabel('Price')
    plt.title('Trade History on Training Data')
    plt.legend()
    plt.grid()
    
    # --- 累積利益の計算と表示 ---
    ax2 = plt.subplot(2, 1, 2, sharex=ax1)
    cumulative_profit = []
    profit = 0
    entry_price = None
    for h in trade_history:
        if h['action'] == 1 and entry_price is None:
            entry_price = h['price']
        elif h['action'] == 2 and entry_price is not None:
            profit += h['price'] - entry_price
            entry_price = None
        cumulative_profit.append(profit)
    plt.plot(df['日時'].iloc[[h['step'] for h in trade_history]], cumulative_profit, label='Cumulative Profit', color='blue')
    plt.xlabel('Datetime')
    plt.ylabel('Cumulative Profit')
    plt.title('Cumulative Profit')
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()

# --- データ準備例（本番では実データを読み込む） ---
# df = pd.read_csv('your_data.csv')
# 必要なカラム: ['出来高','終値','MACD','シグナルライン','前日終値','始値','始値','高値','安値','終値']
# df['MACD'], df['シグナルライン']は事前に計算しておくこと

# --- 学習例 ---
# env = TradingEnv(df)
# model = PPO('MlpPolicy', env, verbose=1)
# model.learn(total_timesteps=100_000)
# model.save('ppo_trading')

# --- 推論例 ---
# obs, _ = env.reset()
# done = False
# while not done:
#     action, _ = model.predict(obs)
#     obs, reward, done, truncated, info = env.step(action)


def main():
    # データの読み込みと前処理
    chart_file = os.path.join(S_INPUT_DIR, 'stock_chart_5M_6758.csv')
    df = pd.read_csv(chart_file)  # 実際のデータファイルを指定

    # Null値を除去
    df = df.dropna().reset_index(drop=True)

    # 日時カラムの変換
    df['日時'] = df['日付'] + ' ' + df['時刻'].fillna('00:00')
    df['日時'] = pd.to_datetime(df['日時'], format='%Y/%m/%d %H:%M')

    # 前日終値の計算
    df['前日終値'] = df['終値'].shift(1)

    # テクニカル指標の計算
    df['MACD'] = df['終値'].ewm(span=12, adjust=False).mean() - df['終値'].ewm(span=26, adjust=False).mean()
    df['シグナルライン'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (df['終値'].diff().clip(lower=0).rolling(window=14).mean() /
                                    df['終値'].diff().clip(upper=0).abs().rolling(window=14).mean())))
    df['MA乖離率'] = (df['終値'] - df['終値'].rolling(window=20).mean()) / df['終値'].rolling(window=20).mean()
    df['出来高比'] = df['出来高'] / df['出来高'].rolling(window=20).mean()
    df['ボラティリティ'] = df['終値'].rolling(window=20).std()

    # NaN, infを0で埋める（全カラム一括）
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)

    # データ表示
    print("データの先頭5行:")
    print(df.head())

    # データの保存
    output_file = os.path.join(S_OUTPUT_DIR, 'processed_stock_data.csv')
    df.to_csv(output_file, index=False)

    # 環境の初期化
    env = TradingEnv(df, n_history=500)  # 必要に応じてn_historyを変更可能

    # モデルの学習
    model_output_dir = os.path.join(S_OUTPUT_DIR, 'model')
    os.makedirs(model_output_dir, exist_ok=True)
    callback = RewardLoggerCallback()
    model = PPO('MlpPolicy', env, verbose=1)
    model.learn(total_timesteps=1_00_000, callback=callback)
    model.save(os.path.join(model_output_dir, 'ppo_trading'))
    # 学習曲線の可視化
    plot_learning_curve(callback.episode_rewards, callback.episode_lengths)

    # --- 売買履歴の可視化 ---
    obs, _ = env.reset()
    done = False
    trade_history = []
    step = 0
    last_position = env.position
    for _ in range(env.episode_start, env.episode_end + 1):
        action, _ = model.predict(obs, deterministic=True)
        price = env.df.iloc[env.current_step]['終値']
        # 実際に売買が成立した場合のみ履歴に記録
        executed = False
        if action == 1 and last_position == 0 and env.position == 0:
            executed = True
        elif action == 2 and last_position == 1 and env.position == 1:
            executed = True
        # ポジション変化時のみ記録
        if executed:
            trade_history.append({
                'step': env.current_step,
                'action': int(action),
                'price': price,
                'position': env.position
            })
        obs, reward, done, truncated, info = env.step(action)
        last_position = env.position
        if done:
            break
    plot_trade_history(env.df, trade_history)
    # --- 売買履歴の可視化（学習データでの検証） ---
    obs, _ = env.reset()
    done = False
    trade_history = []
    step = 0
    last_position = 0
    last_entry_price = None
    cumulative_profit = 0
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        price = env.df.iloc[env.current_step]['終値']
        # 実際に売買が成立した場合のみ履歴に記録
        executed = False
        executed_action = None
        executed_price = None
        if action == 1 and env.position == 0:
            executed = True
            executed_action = 1
            executed_price = price
            last_position = 1
            last_entry_price = price
        elif action == 2 and env.position == 1:
            executed = True
            executed_action = 2
            executed_price = price
            cumulative_profit += price - last_entry_price if last_entry_price is not None else 0
            last_position = 0
            last_entry_price = None
        # 強制決済（1日終了時）
        if env.position == 1 and (env.current_step == env.episode_end or done):
            executed = True
            executed_action = 2
            executed_price = price
            cumulative_profit += price - last_entry_price if last_entry_price is not None else 0
            last_position = 0
            last_entry_price = None
        if executed:
            trade_history.append({
                'step': env.current_step,
                'action': executed_action,
                'price': executed_price,
                'position': last_position,
                'cum_profit': cumulative_profit
            })
        obs, reward, done, truncated, info = env.step(action)
        step += 1
    print(f"学習データでの累積利益: {cumulative_profit}")
    plot_trade_history(env.df, trade_history)


if __name__ == "__main__":
    main()