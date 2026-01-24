"""
設定ファイル検証モジュール
YAML設定ファイルのバリデーションとロードを提供
"""
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """設定ファイル検証エラー"""
    pass


class ConfigValidator:
    """設定ファイルの検証とロード"""
    
    @staticmethod
    def load_backtest_config(config_path: str = "config/backtest_config.yaml") -> Dict[str, Any]:
        """
        バックテスト設定をロード・検証
        
        Args:
            config_path: 設定ファイルパス
            
        Returns:
            検証済み設定辞書
            
        Raises:
            ConfigValidationError: 設定が不正な場合
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise ConfigValidationError(f"設定ファイルが見つかりません: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 必須フィールド検証
        ConfigValidator._validate_required_fields(config, [
            'mode',
            'backtest',
            'data',
            'symbols',
            'output'
        ])
        
        # モード検証
        if config['mode'] not in ['backtest', 'live']:
            raise ConfigValidationError(f"無効なmode: {config['mode']}")
        
        # 日付検証
        try:
            start_date = datetime.strptime(config['backtest']['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(config['backtest']['end_date'], '%Y-%m-%d')
            if start_date > end_date:
                raise ConfigValidationError(
                    f"start_date ({start_date}) が end_date ({end_date}) より後です"
                )
        except ValueError as e:
            raise ConfigValidationError(f"日付フォーマットエラー: {e}")
        
        # lookback_days検証
        lookback_days = config['backtest'].get('lookback_days', 5)
        if not isinstance(lookback_days, int) or lookback_days < 1:
            raise ConfigValidationError(
                f"lookback_daysは1以上の整数である必要があります: {lookback_days}"
            )
        
        logger.info(f"バックテスト設定をロードしました: {config_path}")
        return config
    
    @staticmethod
    def load_level_config(config_path: str = "config/level_config.yaml") -> Dict[str, Any]:
        """
        レベル設定をロード・検証
        
        Args:
            config_path: 設定ファイルパス
            
        Returns:
            検証済み設定辞書
            
        Raises:
            ConfigValidationError: 設定が不正な場合
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise ConfigValidationError(f"設定ファイルが見つかりません: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 必須フィールド検証
        ConfigValidator._validate_required_fields(config, [
            'level_types',
            'common'
        ])
        
        # 各レベルタイプの検証
        for level_type, settings in config['level_types'].items():
            if 'enable' not in settings:
                raise ConfigValidationError(
                    f"level_types.{level_type}にenableフィールドがありません"
                )
            if 'weight' not in settings:
                raise ConfigValidationError(
                    f"level_types.{level_type}にweightフィールドがありません"
                )
            
            # 重みの範囲検証
            weight = settings['weight']
            if not isinstance(weight, (int, float)) or weight < 0 or weight > 1:
                raise ConfigValidationError(
                    f"level_types.{level_type}.weightは0.0-1.0の範囲である必要があります: {weight}"
                )
        
        logger.info(f"レベル設定をロードしました: {config_path}")
        return config
    
    @staticmethod
    def _validate_required_fields(config: Dict[str, Any], required_fields: List[str]) -> None:
        """
        必須フィールドの存在を検証
        
        Args:
            config: 設定辞書
            required_fields: 必須フィールドリスト
            
        Raises:
            ConfigValidationError: 必須フィールドが欠けている場合
        """
        for field in required_fields:
            if field not in config:
                raise ConfigValidationError(f"必須フィールドが不足: {field}")
    
    @staticmethod
    def get_enabled_level_types(level_config: Dict[str, Any]) -> List[str]:
        """
        有効化されているレベルタイプのリストを取得
        
        Args:
            level_config: レベル設定辞書
            
        Returns:
            有効なレベルタイプ名のリスト
        """
        return [
            level_type
            for level_type, settings in level_config['level_types'].items()
            if settings.get('enable', False)
        ]
    
    @staticmethod
    def validate_data_paths(backtest_config: Dict[str, Any], base_dir: Path) -> None:
        """
        データパスの存在を検証
        
        Args:
            backtest_config: バックテスト設定辞書
            base_dir: ベースディレクトリ（通常はalgo4_counter_tradeディレクトリ）
            
        Raises:
            ConfigValidationError: 必要なディレクトリが存在しない場合
        """
        data_config = backtest_config['data']
        
        chart_data_dir = base_dir / data_config['chart_data_dir']
        market_data_dir = base_dir / data_config['market_data_dir']
        
        if not chart_data_dir.exists():
            raise ConfigValidationError(
                f"チャートデータディレクトリが存在しません: {chart_data_dir}"
            )
        
        if not market_data_dir.exists():
            raise ConfigValidationError(
                f"板情報ディレクトリが存在しません: {market_data_dir}"
            )
        
        logger.info("データパスの検証に成功しました")


if __name__ == "__main__":
    # 設定ファイルのテストロード
    logging.basicConfig(level=logging.INFO)
    
    try:
        backtest_config = ConfigValidator.load_backtest_config()
        print("✓ バックテスト設定の検証成功")
        
        level_config = ConfigValidator.load_level_config()
        print("✓ レベル設定の検証成功")
        
        enabled_types = ConfigValidator.get_enabled_level_types(level_config)
        print(f"✓ 有効なレベルタイプ: {enabled_types}")
        
    except ConfigValidationError as e:
        print(f"✗ 設定検証エラー: {e}")
