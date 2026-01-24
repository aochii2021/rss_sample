"""
レベル生成統合モジュール
各種S/Rレベルを設定ベースで生成（ON/OFF制御、データリーク防止）
"""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class LevelGenerator:
    """
    S/Rレベル生成クラス
    
    生成可能なレベルタイプ:
    - pivot_sr: Pivot高値・安値によるS/Rレベル
    - consolidation: 値固め（横ばい）ゾーンのS/Rレベル
    - psychological: キリ番（100円単位、50円単位）のS/Rレベル
    - ma5: 5日移動平均線
    - ma25: 25日移動平均線
    - vpoc: Volume Profile POC（ボリュームピーク）
    """
    
    def __init__(self, level_config: Dict[str, Any]):
        """
        初期化
        
        Args:
            level_config: レベル設定（level_config.yaml）
        """
        self.level_config = level_config
        self.level_types = level_config['level_types']
        self.common_config = level_config['common']
        
        # 有効なレベルタイプをログ出力
        enabled = [name for name, cfg in self.level_types.items() if cfg.get('enable', False)]
        logger.info(f"有効なレベルタイプ: {enabled}")
    
    def generate(
        self,
        target_date: datetime,
        chart_data: Dict[str, pd.DataFrame],
        ohlc_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        全銘柄のS/Rレベルを生成
        
        Args:
            target_date: 対象日（この日より前のデータのみ使用）
            chart_data: チャートデータ（日足・分足）
            ohlc_data: OHLC data（分足）
            
        Returns:
            {銘柄コード: [レベル辞書リスト]} の辞書
        """
        logger.info(f"レベル生成開始: target_date={target_date.strftime('%Y-%m-%d')}")
        
        all_levels = {}
        symbols = set(chart_data.keys()) | set(ohlc_data.keys())
        
        for symbol in symbols:
            try:
                symbol_levels = self._generate_for_symbol(
                    symbol,
                    target_date,
                    chart_data.get(symbol),
                    ohlc_data.get(symbol)
                )
                
                # 品質フィルタリング
                symbol_levels = self._filter_levels(symbol_levels, symbol)
                
                all_levels[symbol] = symbol_levels
                logger.info(f"  {symbol}: {len(symbol_levels)}個のレベル生成")
                
            except Exception as e:
                import traceback
                logger.error(f"  {symbol}: レベル生成エラー - {e}\n{traceback.format_exc()}")
                all_levels[symbol] = []
        
        logger.info(f"レベル生成完了: {sum(len(v) for v in all_levels.values())}個")
        return all_levels
    
    def _generate_for_symbol(
        self,
        symbol: str,
        target_date: datetime,
        chart_df: Optional[pd.DataFrame],
        ohlc_df: Optional[pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """
        1銘柄のレベルを生成
        
        Args:
            symbol: 銘柄コード
            target_date: 対象日
            chart_df: チャートデータ
            ohlc_df: OHLCデータ
            
        Returns:
            レベル辞書リスト
        """
        levels = []
        
        # Pivot S/R
        if self.level_types.get('pivot_sr', {}).get('enable', False):
            pivot_levels = self._generate_pivot_sr(symbol, target_date, ohlc_df)
            levels.extend(pivot_levels)
        
        # Consolidation
        if self.level_types.get('consolidation', {}).get('enable', False):
            consol_levels = self._generate_consolidation(symbol, target_date, chart_df)
            levels.extend(consol_levels)
        
        # Psychological
        if self.level_types.get('psychological', {}).get('enable', False):
            psych_levels = self._generate_psychological(symbol, target_date, chart_df, ohlc_df)
            levels.extend(psych_levels)
        
        # MA5
        if self.level_types.get('ma5', {}).get('enable', False):
            ma5_levels = self._generate_ma(symbol, target_date, chart_df, period=5, kind='ma5')
            levels.extend(ma5_levels)
        
        # MA25
        if self.level_types.get('ma25', {}).get('enable', False):
            ma25_levels = self._generate_ma(symbol, target_date, chart_df, period=25, kind='ma25')
            levels.extend(ma25_levels)
        
        # VPOC（将来実装）
        if self.level_types.get('vpoc', {}).get('enable', False):
            logger.debug(f"  {symbol}: VPOCは未実装")
        
        return levels
    
    def _generate_pivot_sr(
        self,
        symbol: str,
        target_date: datetime,
        ohlc_df: Optional[pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """
        Pivot高値・安値からS/Rレベルを生成
        
        Args:
            symbol: 銘柄コード
            target_date: 対象日
            ohlc_df: OHLCデータ
            
        Returns:
            レベル辞書リスト
        """
        if ohlc_df is None or ohlc_df.empty:
            return []
        
        config = self.level_config['pivot_sr']
        lookback_days = config['lookback_days']
        min_distance = config['peak_detection']['min_distance']
        prominence = config['peak_detection']['prominence']
        
        # target_date以前のデータのみ使用
        df = ohlc_df[ohlc_df['timestamp'] < target_date].copy()
        
        if df.empty:
            return []
        
        # 直近N日分のデータ取得
        df = df.tail(lookback_days * 390)  # 1日≒390本（1分足）
        
        if len(df) < min_distance * 2:
            return []
        
        levels = []
        weight = self.level_types['pivot_sr']['weight']
        
        # 高値ピーク検出
        high_peaks, properties = find_peaks(
            df['high'].values,
            distance=min_distance,
            prominence=prominence
        )
        
        for idx in high_peaks:
            price = float(df.iloc[idx]['high'])
            timestamp = df.iloc[idx]['timestamp']
            
            levels.append({
                'kind': 'pivot_high',
                'symbol': symbol,
                'level_now': price,
                'strength': weight,
                'timestamp': timestamp,
                'meta': {'lookback_days': lookback_days}
            })
        
        # 安値ピーク検出
        low_peaks, properties = find_peaks(
            -df['low'].values,
            distance=min_distance,
            prominence=prominence
        )
        
        for idx in low_peaks:
            price = float(df.iloc[idx]['low'])
            timestamp = df.iloc[idx]['timestamp']
            
            levels.append({
                'kind': 'pivot_low',
                'symbol': symbol,
                'level_now': price,
                'strength': weight,
                'timestamp': timestamp,
                'meta': {'lookback_days': lookback_days}
            })
        
        # 同一価格帯のレベル統合
        levels = self._merge_nearby_levels(levels, config['merge_threshold_percent'])
        
        return levels
    
    def _generate_consolidation(
        self,
        symbol: str,
        target_date: datetime,
        chart_df: Optional[pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """
        値固め（横ばい）ゾーンからS/Rレベルを生成
        
        Args:
            symbol: 銘柄コード
            target_date: 対象日
            chart_df: チャートデータ（日足）
            
        Returns:
            レベル辞書リスト
        """
        if chart_df is None or chart_df.empty:
            return []
        
        config = self.level_config['consolidation']
        lookback_days = config['lookback_days']
        min_duration = config['detection']['min_duration']
        max_range_pct = config['detection']['max_price_range_percent']
        
        # target_date以前のデータのみ使用
        df = chart_df[chart_df['timestamp'] < target_date].copy()
        
        if df.empty:
            return []
        
        # 直近N日分取得
        df = df.tail(lookback_days)
        
        if len(df) < min_duration:
            return []
        
        levels = []
        weight = self.level_types['consolidation']['weight']
        
        # ローリングウィンドウで値固めゾーン検出
        for i in range(len(df) - min_duration + 1):
            window = df.iloc[i:i + min_duration]
            
            high_max = window['high'].max()
            low_min = window['low'].min()
            mid = (high_max + low_min) / 2
            
            if mid == 0:
                continue
            
            price_range_pct = (high_max - low_min) / mid * 100
            
            if price_range_pct <= max_range_pct:
                # 値固めゾーン検出
                level_price = mid
                
                levels.append({
                    'kind': 'consolidation',
                    'symbol': symbol,
                    'level_now': float(level_price),
                    'strength': weight,
                    'timestamp': window.iloc[-1]['timestamp'],
                    'meta': {
                        'duration': len(window),
                        'range_pct': float(price_range_pct)
                    }
                })
        
        # 統合
        levels = self._merge_nearby_levels(levels, config['merge_threshold_percent'])
        
        return levels
    
    def _generate_psychological(
        self,
        symbol: str,
        target_date: datetime,
        chart_df: Optional[pd.DataFrame],
        ohlc_df: Optional[pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """
        キリ番（心理的価格帯）からS/Rレベルを生成
        
        Args:
            symbol: 銘柄コード
            target_date: 対象日
            chart_df: チャートデータ
            ohlc_df: OHLCデータ
            
        Returns:
            レベル辞書リスト
        """
        # 現在価格を取得
        df = chart_df if chart_df is not None and not chart_df.empty else ohlc_df
        
        if df is None or df.empty:
            return []
        
        # target_date以前のデータ
        df = df[df['timestamp'] < target_date]
        
        if df.empty:
            return []
        
        current_price = float(df.iloc[-1]['close'] if 'close' in df.columns else df.iloc[-1]['mid'])
        
        config = self.level_config['psychological']
        weight = self.level_types['psychological']['weight']
        
        # 価格帯に応じたキリ番粒度を決定
        round_to = None
        for range_config in config['price_ranges']:
            min_price = range_config.get('min', 0)
            max_price = range_config.get('max', float('inf'))
            
            if min_price <= current_price < max_price:
                round_to = range_config['round_to']
                break
        
        if round_to is None:
            return []
        
        levels = []
        
        # 現在価格の上下±10%の範囲でキリ番を生成
        price_min = current_price * 0.9
        price_max = current_price * 1.1
        
        current_level = (int(price_min / round_to) + 1) * round_to
        
        while current_level <= price_max:
            levels.append({
                'kind': 'psychological',
                'symbol': symbol,
                'level_now': float(current_level),
                'strength': weight,
                'timestamp': target_date,
                'meta': {'round_to': round_to}
            })
            current_level += round_to
        
        return levels
    
    def _generate_ma(
        self,
        symbol: str,
        target_date: datetime,
        chart_df: Optional[pd.DataFrame],
        period: int,
        kind: str
    ) -> List[Dict[str, Any]]:
        """
        移動平均線からS/Rレベルを生成
        
        Args:
            symbol: 銘柄コード
            target_date: 対象日
            chart_df: チャートデータ（日足）
            period: MA期間
            kind: 'ma5' or 'ma25'
            
        Returns:
            レベル辞書リスト
        """
        if chart_df is None or chart_df.empty:
            return []
        
        # target_date以前のデータ
        df = chart_df[chart_df['timestamp'] < target_date].copy()
        
        if df.empty or len(df) < period:
            return []
        
        # 終値で移動平均を計算
        df['ma'] = df['close'].rolling(window=period).mean()
        
        # 最新のMA値を取得
        latest_ma = df.iloc[-1]['ma']
        
        if pd.isna(latest_ma):
            return []
        
        weight = self.level_types[kind]['weight']
        
        return [{
            'kind': kind,
            'symbol': symbol,
            'level_now': float(latest_ma),
            'strength': weight,
            'timestamp': df.iloc[-1]['timestamp'],
            'meta': {'period': period}
        }]
    
    def _merge_nearby_levels(
        self,
        levels: List[Dict[str, Any]],
        threshold_percent: float
    ) -> List[Dict[str, Any]]:
        """
        近接するレベルを統合
        
        Args:
            levels: レベルリスト
            threshold_percent: 統合閾値（パーセント）
            
        Returns:
            統合後のレベルリスト
        """
        if not levels:
            return []
        
        # 価格でソート
        sorted_levels = sorted(levels, key=lambda x: x['level_now'])
        merged = []
        
        i = 0
        while i < len(sorted_levels):
            current = sorted_levels[i]
            cluster = [current]
            
            # 閾値内の近接レベルを収集
            j = i + 1
            while j < len(sorted_levels):
                next_level = sorted_levels[j]
                price_diff_pct = abs(next_level['level_now'] - current['level_now']) / current['level_now'] * 100
                
                if price_diff_pct <= threshold_percent:
                    cluster.append(next_level)
                    j += 1
                else:
                    break
            
            # クラスタの平均価格を計算
            avg_price = sum(lv['level_now'] for lv in cluster) / len(cluster)
            avg_strength = sum(lv['strength'] for lv in cluster) / len(cluster)
            
            merged.append({
                'kind': current['kind'],
                'symbol': current['symbol'],
                'level_now': float(avg_price),
                'strength': float(avg_strength),
                'timestamp': current['timestamp'],
                'meta': {**current.get('meta', {}), 'merged_count': len(cluster)}
            })
            
            i = j
        
        return merged
    
    def _filter_levels(
        self,
        levels: List[Dict[str, Any]],
        symbol: str
    ) -> List[Dict[str, Any]]:
        """
        レベルの品質フィルタリング
        
        Args:
            levels: レベルリスト
            symbol: 銘柄コード
            
        Returns:
            フィルタリング後のレベルリスト
        """
        if not self.common_config.get('quality_filter', {}).get('enable', False):
            return levels
        
        min_weight = self.common_config['quality_filter'].get('min_weight', 0.3)
        max_levels = self.common_config.get('max_levels_per_symbol', 20)
        
        # 最小重み未満を除外
        filtered = [lv for lv in levels if lv['strength'] >= min_weight]
        
        # 重みでソートして上位N件
        filtered = sorted(filtered, key=lambda x: x['strength'], reverse=True)[:max_levels]
        
        logger.debug(f"  {symbol}: {len(levels)}件 → {len(filtered)}件（フィルタリング後）")
        
        return filtered


if __name__ == "__main__":
    # テスト実行
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.data_loader import DataLoader
    from processors.ohlc_processor import OHLCProcessor
    from utils.config_validator import ConfigValidator
    from datetime import datetime
    
    logging.basicConfig(level=logging.INFO)
    
    # 設定ロード
    level_config = ConfigValidator.load_level_config("config/level_config.yaml")
    
    # データ読み込み
    loader = DataLoader(
        chart_data_dir="input/chart_data",
        market_data_dir="input/market_order_book"
    )
    target_date = datetime(2026, 1, 20)
    
    chart_data = loader.load_chart_data_until(target_date, lookback_days=5)
    market_data = loader.load_market_data_for_date(target_date)
    
    # OHLC生成
    ohlc_processor = OHLCProcessor(freq='1min')
    ohlc_data = ohlc_processor.process(market_data)
    
    # レベル生成
    generator = LevelGenerator(level_config)
    levels = generator.generate(target_date, chart_data, ohlc_data)
    
    print(f"\n=== レベル生成結果 ===")
    for symbol, level_list in list(levels.items())[:3]:
        print(f"\n{symbol}: {len(level_list)}個のレベル")
        for lv in level_list[:5]:
            print(f"  {lv['kind']:15s} {lv['level_now']:10.2f} (強度: {lv['strength']:.2f})")
