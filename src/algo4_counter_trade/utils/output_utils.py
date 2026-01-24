"""
出力管理ユーティリティモジュール
出力ディレクトリ管理、設定スナップショット保存、ログ設定を提供
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import shutil
import yaml
import json
import logging

logger = logging.getLogger(__name__)


class OutputManager:
    """出力ディレクトリとファイルの管理"""
    
    def __init__(self, base_output_dir: str = "output"):
        """
        初期化
        
        Args:
            base_output_dir: 出力ベースディレクトリ
        """
        self.base_output_dir = Path(base_output_dir)
        self.current_output_dir: Optional[Path] = None
        self.timestamp: Optional[str] = None
    
    def create_timestamped_output_dir(
        self,
        timestamp_format: str = "%Y%m%d_%H%M%S"
    ) -> Path:
        """
        タイムスタンプ付き出力ディレクトリを作成
        
        Args:
            timestamp_format: タイムスタンプフォーマット（strftime形式）
            
        Returns:
            作成された出力ディレクトリのパス
        """
        self.timestamp = datetime.now().strftime(timestamp_format)
        self.current_output_dir = self.base_output_dir / self.timestamp
        
        # ディレクトリ作成
        self.current_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"出力ディレクトリを作成: {self.current_output_dir}")
        return self.current_output_dir
    
    def save_config_snapshot(
        self,
        backtest_config: Dict[str, Any],
        level_config: Dict[str, Any],
        trade_params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        設定のスナップショットを保存
        
        Args:
            backtest_config: バックテスト設定
            level_config: レベル設定
            trade_params: トレードパラメータ（オプション）
        """
        if self.current_output_dir is None:
            raise ValueError("出力ディレクトリが未作成です。create_timestamped_output_dir()を先に呼んでください")
        
        # バックテスト設定保存
        backtest_config_path = self.current_output_dir / "backtest_config_snapshot.yaml"
        with open(backtest_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(backtest_config, f, allow_unicode=True, default_flow_style=False)
        logger.info(f"バックテスト設定を保存: {backtest_config_path}")
        
        # レベル設定保存
        level_config_path = self.current_output_dir / "level_config_snapshot.yaml"
        with open(level_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(level_config, f, allow_unicode=True, default_flow_style=False)
        logger.info(f"レベル設定を保存: {level_config_path}")
        
        # トレードパラメータ保存（あれば）
        if trade_params is not None:
            trade_params_path = self.current_output_dir / "trade_params_snapshot.json"
            with open(trade_params_path, 'w', encoding='utf-8') as f:
                json.dump(trade_params, f, ensure_ascii=False, indent=2)
            logger.info(f"トレードパラメータを保存: {trade_params_path}")
    
    def create_latest_link(self) -> None:
        """
        最新実行結果へのシンボリックリンク/コピーを作成
        （Windows環境ではコピーで代替）
        """
        if self.current_output_dir is None:
            raise ValueError("出力ディレクトリが未作成です")
        
        latest_path = self.base_output_dir / "latest"
        
        # 既存のlatestリンク/ディレクトリを削除
        if latest_path.exists():
            if latest_path.is_symlink():
                latest_path.unlink()
            elif latest_path.is_dir():
                shutil.rmtree(latest_path)
        
        # Windowsではシンボリックリンク作成に権限が必要なため、コピーで代替
        try:
            # シンボリックリンク作成を試行
            latest_path.symlink_to(self.current_output_dir, target_is_directory=True)
            logger.info(f"latestリンクを作成: {latest_path} -> {self.current_output_dir}")
        except OSError:
            # シンボリックリンク作成失敗時はコピー
            shutil.copytree(self.current_output_dir, latest_path)
            logger.info(f"latestディレクトリをコピー作成: {latest_path}")
    
    def get_output_path(self, filename: str) -> Path:
        """
        出力ファイルのフルパスを取得
        
        Args:
            filename: ファイル名
            
        Returns:
            フルパス
        """
        if self.current_output_dir is None:
            raise ValueError("出力ディレクトリが未作成です")
        
        return self.current_output_dir / filename
    
    def setup_logging(
        self,
        log_level: str = "INFO",
        log_to_file: bool = True,
        log_file_name: str = "backtest.log"
    ) -> None:
        """
        ロギング設定
        
        Args:
            log_level: ログレベル（DEBUG, INFO, WARNING, ERROR）
            log_to_file: ファイルへのログ出力を有効化
            log_file_name: ログファイル名
        """
        # ログレベル設定
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # ルートロガー設定
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # 既存のハンドラをクリア
        root_logger.handlers.clear()
        
        # フォーマッタ
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # コンソールハンドラ
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # ファイルハンドラ
        if log_to_file:
            if self.current_output_dir is None:
                raise ValueError("出力ディレクトリが未作成です")
            
            log_file_path = self.current_output_dir / log_file_name
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            logger.info(f"ログファイルを設定: {log_file_path}")
        
        logger.info(f"ロギング設定完了: レベル={log_level}")
    
    def cleanup_old_outputs(self, keep_latest_n: int = 10) -> None:
        """
        古い出力ディレクトリをクリーンアップ
        
        Args:
            keep_latest_n: 保持する最新N件の出力
        """
        if not self.base_output_dir.exists():
            return
        
        # タイムスタンプディレクトリのみ取得
        output_dirs = [
            d for d in self.base_output_dir.iterdir()
            if d.is_dir() and d.name != "latest" and not d.name.endswith("_backup")
        ]
        
        # 作成日時でソート（降順）
        output_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # keep_latest_n件を超える古いディレクトリを削除
        for old_dir in output_dirs[keep_latest_n:]:
            shutil.rmtree(old_dir)
            logger.info(f"古い出力ディレクトリを削除: {old_dir}")
        
        logger.info(f"出力クリーンアップ完了: {len(output_dirs[keep_latest_n:])}件削除")


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    # OutputManager初期化
    output_mgr = OutputManager(base_output_dir="test_output")
    
    # 出力ディレクトリ作成
    output_dir = output_mgr.create_timestamped_output_dir()
    print(f"作成された出力ディレクトリ: {output_dir}")
    
    # ロギング設定
    output_mgr.setup_logging(log_level="DEBUG", log_to_file=True)
    
    # 設定スナップショット保存テスト
    test_backtest_config = {
        "mode": "backtest",
        "backtest": {
            "start_date": "2026-01-19",
            "end_date": "2026-01-23"
        }
    }
    test_level_config = {
        "level_types": {
            "pivot_sr": {"enable": True, "weight": 1.0}
        }
    }
    
    output_mgr.save_config_snapshot(test_backtest_config, test_level_config)
    
    # 出力ファイルパス取得テスト
    trades_path = output_mgr.get_output_path("trades.csv")
    print(f"出力ファイルパス: {trades_path}")
    
    # latestリンク作成テスト
    output_mgr.create_latest_link()
    print("✓ OutputManager テスト完了")
