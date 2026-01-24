#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
統合バックテストシステム - メインエントリーポイント

設定ファイルベースで以下を実行:
1. データ読み込み（データリーク防止）
2. S/Rレベル生成（ON/OFF制御）
3. バックテスト実行
4. 結果出力（タイムスタンプ付きディレクトリ）

使用例:
    python main.py
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from utils.config_validator import ConfigValidator, ConfigValidationError
from utils.date_utils import DateUtils
from utils.output_utils import OutputManager
from config.trade_params import get_params, is_excluded

logger = logging.getLogger(__name__)


class UnifiedBacktest:
    """統合バックテストシステム"""
    
    def __init__(self, base_dir: Path = None):
        """
        初期化
        
        Args:
            base_dir: ベースディレクトリ（デフォルトはスクリプト実行位置）
        """
        self.base_dir = base_dir or Path(__file__).parent
        self.backtest_config: Dict[str, Any] = {}
        self.level_config: Dict[str, Any] = {}
        self.output_manager: OutputManager = None
        
    def load_configs(self) -> None:
        """設定ファイルをロード・検証"""
        logger.info("=" * 60)
        logger.info("設定ファイル読み込み開始")
        logger.info("=" * 60)
        
        try:
            # バックテスト設定
            self.backtest_config = ConfigValidator.load_backtest_config(
                str(self.base_dir / "config" / "backtest_config.yaml")
            )
            logger.info(f"✓ バックテスト設定: mode={self.backtest_config['mode']}")
            logger.info(
                f"  期間: {self.backtest_config['backtest']['start_date']} ～ "
                f"{self.backtest_config['backtest']['end_date']}"
            )
            
            # レベル設定
            self.level_config = ConfigValidator.load_level_config(
                str(self.base_dir / "config" / "level_config.yaml")
            )
            enabled_types = ConfigValidator.get_enabled_level_types(self.level_config)
            logger.info(f"✓ レベル設定: 有効タイプ={enabled_types}")
            
            # データパス検証
            ConfigValidator.validate_data_paths(self.backtest_config, self.base_dir)
            logger.info("✓ データパス検証完了")
            
        except ConfigValidationError as e:
            logger.error(f"設定ファイルエラー: {e}")
            raise
        except Exception as e:
            logger.error(f"予期しないエラー: {e}")
            raise
    
    def setup_output(self) -> None:
        """出力ディレクトリとロギングを設定"""
        logger.info("=" * 60)
        logger.info("出力環境セットアップ")
        logger.info("=" * 60)
        
        # OutputManager初期化
        output_base = self.backtest_config['data']['output_base_dir']
        self.output_manager = OutputManager(output_base)
        
        # タイムスタンプ付きディレクトリ作成
        output_format = self.backtest_config['output'].get('output_dir_format', '%Y%m%d_%H%M%S')
        output_dir = self.output_manager.create_timestamped_output_dir(output_format)
        
        # ロギング再設定（ファイル出力追加）
        log_config = self.backtest_config.get('logging', {})
        self.output_manager.setup_logging(
            log_level=log_config.get('level', 'INFO'),
            log_to_file=log_config.get('log_file', True),
            log_file_name='backtest.log'
        )
        
        logger.info(f"✓ 出力ディレクトリ: {output_dir}")
        
        # 設定スナップショット保存
        self.output_manager.save_config_snapshot(
            self.backtest_config,
            self.level_config
        )
        logger.info("✓ 設定スナップショット保存完了")
    
    def phase1_load_data(self, target_date: datetime) -> Dict[str, Any]:
        """
        Phase 1: データ読み込み（データリーク防止）
        
        Args:
            target_date: バックテスト対象日
            
        Returns:
            ロードしたデータ辞書
        """
        logger.info("-" * 60)
        logger.info(f"Phase 1: データ読み込み - {target_date.strftime('%Y-%m-%d')}")
        logger.info("-" * 60)
        
        # TODO: core.data_loader.DataLoaderを使用
        # - load_chart_data_until(target_date)
        # - load_market_data_for_date(target_date)
        # - 未来データチェック
        
        logger.info("Phase 1: 未実装（スタブ）")
        return {}
    
    def phase2_generate_levels(
        self,
        target_date: datetime,
        chart_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 2: S/Rレベル生成
        
        Args:
            target_date: バックテスト対象日
            chart_data: チャートデータ
            
        Returns:
            生成されたレベル辞書
        """
        logger.info("-" * 60)
        logger.info(f"Phase 2: レベル生成 - {target_date.strftime('%Y-%m-%d')}")
        logger.info("-" * 60)
        
        # TODO: core.level_generator.LevelGeneratorを使用
        # - level_config.yamlに基づいてON/OFFを制御
        # - データリーク防止: target_date以前のデータのみ使用
        
        enabled_types = ConfigValidator.get_enabled_level_types(self.level_config)
        logger.info(f"有効なレベルタイプ: {enabled_types}")
        logger.info("Phase 2: 未実装（スタブ）")
        return {}
    
    def phase3_process_lob_features(
        self,
        target_date: datetime,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 3: LOB特徴量計算
        
        Args:
            target_date: バックテスト対象日
            market_data: 板情報データ
            
        Returns:
            LOB特徴量辞書
        """
        logger.info("-" * 60)
        logger.info(f"Phase 3: LOB特徴量計算 - {target_date.strftime('%Y-%m-%d')}")
        logger.info("-" * 60)
        
        # TODO: processors.lob_processor.LOBProcessorを使用
        
        logger.info("Phase 3: 未実装（スタブ）")
        return {}
    
    def phase4_run_backtest(
        self,
        target_date: datetime,
        levels: Dict[str, Any],
        lob_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 4: バックテスト実行
        
        Args:
            target_date: バックテスト対象日
            levels: S/Rレベル
            lob_features: LOB特徴量
            
        Returns:
            バックテスト結果
        """
        logger.info("-" * 60)
        logger.info(f"Phase 4: バックテスト実行 - {target_date.strftime('%Y-%m-%d')}")
        logger.info("-" * 60)
        
        # TODO: core.backtest_engine.BacktestEngineを使用
        
        logger.info("Phase 4: 未実装（スタブ）")
        return {}
    
    def phase5_save_results(self, results: Dict[str, Any]) -> None:
        """
        Phase 5: 結果保存
        
        Args:
            results: バックテスト結果
        """
        logger.info("-" * 60)
        logger.info("Phase 5: 結果保存")
        logger.info("-" * 60)
        
        # TODO: output_handlers.result_writer.ResultWriterを使用
        # - trades.csv
        # - backtest_summary.json
        # - levels.jsonl
        
        logger.info("Phase 5: 未実装（スタブ）")
        
        # latestリンク/コピー作成
        self.output_manager.create_latest_link()
        logger.info("✓ 最新結果へのリンク作成完了")
    
    def run(self) -> None:
        """メインバックテスト実行"""
        try:
            # 設定ロード
            self.load_configs()
            
            # 出力セットアップ
            self.setup_output()
            
            logger.info("=" * 60)
            logger.info("バックテスト実行開始")
            logger.info("=" * 60)
            
            # バックテスト期間の営業日を取得
            start_date = datetime.strptime(
                self.backtest_config['backtest']['start_date'],
                '%Y-%m-%d'
            )
            end_date = datetime.strptime(
                self.backtest_config['backtest']['end_date'],
                '%Y-%m-%d'
            )
            business_days = DateUtils.get_business_days_between(start_date, end_date)
            
            logger.info(f"対象営業日: {len(business_days)}日")
            for day in business_days:
                logger.info(f"  - {day.strftime('%Y-%m-%d (%a)')}")
            
            # 全結果を集約
            all_results = []
            
            # 各営業日でバックテスト実行
            for target_date in business_days:
                logger.info("")
                logger.info("=" * 60)
                logger.info(f"処理開始: {target_date.strftime('%Y-%m-%d')}")
                logger.info("=" * 60)
                
                # Phase 1: データ読み込み
                data = self.phase1_load_data(target_date)
                
                # Phase 2: レベル生成
                levels = self.phase2_generate_levels(target_date, data)
                
                # Phase 3: LOB特徴量計算
                lob_features = self.phase3_process_lob_features(target_date, data)
                
                # Phase 4: バックテスト実行
                daily_results = self.phase4_run_backtest(target_date, levels, lob_features)
                all_results.append(daily_results)
                
                logger.info(f"✓ {target_date.strftime('%Y-%m-%d')} 完了")
            
            # Phase 5: 結果保存
            self.phase5_save_results(all_results)
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("バックテスト完了")
            logger.info("=" * 60)
            logger.info(f"結果出力先: {self.output_manager.current_output_dir}")
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error("エラーが発生しました")
            logger.error("=" * 60)
            logger.exception(e)
            raise


def main():
    """エントリーポイント"""
    print("=" * 60)
    print("統合バックテストシステム")
    print("=" * 60)
    print()
    
    # 初期ロギング設定（コンソールのみ）
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    try:
        backtest = UnifiedBacktest()
        backtest.run()
        
        print()
        print("=" * 60)
        print("✓ 正常終了")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print()
        print("=" * 60)
        print("ユーザーによる中断")
        print("=" * 60)
        sys.exit(1)
        
    except Exception as e:
        print()
        print("=" * 60)
        print("✗ エラー終了")
        print("=" * 60)
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
