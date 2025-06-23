# 強化学習による自動売買アルゴリズム（PPO/SAC対応）
# 必要なライブラリ: stable-baselines3, gymnasium, numpy, pandas
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
# from stable_baselines3 import SAC  # SACを使いたい場合はこちら

# --- 環境クラス定義 ---


class TradingEnv(gym.Env):
    def __init__(self, df: pd.DataFrame, initial_balance=1_000_000):
        super().__init__()
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.action_space = spaces.Discrete(3)  # 0:何もしない, 1:買い, 2:売り
        # 状態空間: 価格帯別出来高(3000), 現在値, MACD, シグナル, PER, PBR, 前日終値, 当日始値, ロウソク足(3000*4), 建玉
        n_price_bins = 3000
        n_candle = 3000 * 4
        obs_dim = n_price_bins + 7 + n_candle + 1
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
        # その他指標
        now = self.df.iloc[self.current_step]
        obs = np.concatenate([
            volume_by_price,
            [now['終値'], now['MACD'], now['シグナルライン'],
                now['PER'], now['PBR'], now['前日終値'], now['始値']],
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
# 必要なカラム: ['出来高','終値','MACD','シグナルライン','PER','PBR','前日終値','始値','始値','高値','安値','終値']
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
