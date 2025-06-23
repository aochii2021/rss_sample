# 強化学習による自動売買アルゴリズム（PPO/SAC対応）
# 必要なライブラリ: stable-baselines3, gymnasium, numpy, pandas
import os
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
# from stable_baselines3 import SAC  # SACを使いたい場合はこちら

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# 出力ディレクトリの設定
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')
# 入力ディレクトリの設定
S_INPUT_DIR = os.path.join(S_FILE_DIR, 'input')

# --- 環境クラス定義 ---


class TradingEnv(gym.Env):
    def __init__(self, df: pd.DataFrame, initial_balance=1_000_000):
        super().__init__()
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.action_space = spaces.Discrete(3)  # 0:何もしない, 1:買い, 2:売り
        # 状態空間: 価格帯別出来高(3000), 現在値, MACD, シグナル, 前日終値, 当日始値, ロウソク足(3000*4), 建玉, RSI, MA乖離率, 出来高比, ボラティリティ
        n_price_bins = 3000
        n_candle = 3000 * 4
        obs_dim = n_price_bins + 8 + n_candle + 1  # PER/PBR削除、短期指標4種追加
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)
        self.reset()

    def reset(self, seed=None, options=None):
        self.balance = self.initial_balance
        self.position = 0  # 0:ノーポジ, 1:買い, -1:売り
        self.current_step = 3000  # 3000本目からスタート
        self.done = False
        return self._get_obs(), {}

    def _get_obs(self):
        # 価格帯別出来高
        volume_by_price = self.df['出来高'].iloc[self.current_step -
                                              3000:self.current_step].values
        # ロウソク足（Open, High, Low, Close）
        candle = self.df[['始値', '高値', '安値', '終値']
                         ].iloc[self.current_step-3000:self.current_step].values.flatten()
        # 短期トレード向け指標
        now = self.df.iloc[self.current_step]
        rsi = now.get('RSI', 0.0)
        ma_kairi = now.get('MA乖離率', 0.0)
        vol_ratio = now.get('出来高比', 0.0)
        volatility = now.get('ボラティリティ', 0.0)
        obs = np.concatenate([
            volume_by_price,
            [now['終値'], now['MACD'], now['シグナルライン'],
                now['前日終値'], now['始値'], rsi, ma_kairi, vol_ratio, volatility],
            candle,
            [self.position]
        ])
        return obs.astype(np.float32)

    def step(self, action):
        reward = 0
        prev_price = self.df.iloc[self.current_step]['終値']
        self.current_step += 1
        if self.current_step >= len(self.df):
            self.done = True
        now_price = self.df.iloc[self.current_step]['終値']
        # シンプルな報酬: ポジション変化時の損益
        if action == 1 and self.position == 0:  # 買い
            self.position = 1
            self.entry_price = now_price
        elif action == 2 and self.position == 1:  # 売り
            reward = now_price - self.entry_price
            self.position = 0
        elif action == 0:
            reward = 0
        return self._get_obs(), reward, self.done, False, {}

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
    df['MACD'] = df['終値'].ewm(span=12, adjust=False).mean() - df['終値'].ewm(span=26, adjust=False).mean()
    df['シグナルライン'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (df['終値'].diff().clip(lower=0).rolling(window=14).mean() /
                                    df['終値'].diff().clip(upper=0).abs().rolling(window=14).mean())))
    df['MA乖離率'] = (df['終値'] - df['終値'].rolling(window=20).mean()) / df['終値'].rolling(window=20).mean()
    df['出来高比'] = df['出来高'] / df['出来高'].rolling(window=20).mean()
    df['ボラティリティ'] = df['終値'].rolling(window=20).std()

    # データ表示
    print("データの先頭5行:")
    print(df.head())

    # データの保存
    output_file = os.path.join(S_OUTPUT_DIR, 'processed_stock_data.csv')
    df.to_csv(output_file, index=False)

    # 環境の初期化
    env = TradingEnv(df)

    # モデルの学習
    model = PPO('MlpPolicy', env, verbose=1)
    model.learn(total_timesteps=100_000)
    model.save('ppo_trading')


if __name__ == "__main__":
    main()