#!/usr/bin/env python3
"""
Setup Wizard untuk AI Trading Agent.
Interactive configuration untuk parameter trading.
"""
import yaml
import os


def print_header():
    print("\n" + "="*60)
    print("🤖 AI TRADING AGENT - SETUP WIZARD")
    print("="*60 + "\n")


def get_input(prompt, default, validator=None):
    """Get user input dengan default value dan validator"""
    while True:
        user_input = input(f"{prompt} [{default}]: ").strip()
        value = user_input if user_input else default
        
        if validator:
            valid, error = validator(value)
            if not valid:
                print(f"❌ {error}")
                continue
        
        return value


def validate_symbol(value):
    """Validate trading symbol"""
    valid_symbols = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD']
    if value.upper() not in valid_symbols:
        return False, f"Symbol harus salah satu dari: {', '.join(valid_symbols)}"
    return True, None


def validate_positive_float(value):
    """Validate positive float"""
    try:
        val = float(value)
        if val <= 0:
            return False, "Nilai harus lebih besar dari 0"
        return True, None
    except ValueError:
        return False, "Nilai harus berupa angka"


def validate_positive_int(value):
    """Validate positive integer"""
    try:
        val = int(value)
        if val <= 0:
            return False, "Nilai harus lebih besar dari 0"
        return True, None
    except ValueError:
        return False, "Nilai harus berupa angka bulat"


def validate_percentage(value):
    """Validate percentage (0-100)"""
    try:
        val = float(value)
        if val <= 0 or val > 100:
            return False, "Nilai harus antara 0-100"
        return True, None
    except ValueError:
        return False, "Nilai harus berupa angka"


def validate_mode(value):
    """Validate trading mode"""
    if value.lower() not in ['assisted', 'auto']:
        return False, "Mode harus 'assisted' atau 'auto'"
    return True, None


def validate_provider(value):
    """Validate AI provider"""
    return True, None  # 9Router single provider


def main():
    print_header()
    
    print("Setup wizard akan membantu Anda mengkonfigurasi trading agent.")
    print("Tekan Enter untuk menggunakan nilai default.\n")
    
    # Trading Parameters
    print("📊 TRADING PARAMETERS")
    print("-" * 60)
    
    symbol = get_input(
        "Instrument/Symbol",
        "XAUUSD",
        validate_symbol
    ).upper()
    
    capital = get_input(
        "Modal/Capital (USC)",
        "2000",
        validate_positive_float
    )
    
    lot = get_input(
        "Lot Size",
        "0.01",
        validate_positive_float
    )
    
    max_trades = get_input(
        "Max Trades Per Day",
        "3",
        validate_positive_int
    )
    
    # Risk Parameters
    print("\n⚠️  RISK MANAGEMENT")
    print("-" * 60)
    
    confidence = get_input(
        "Confidence Threshold (%)",
        "80",
        validate_percentage
    )
    
    max_drawdown = get_input(
        "Max Drawdown Per Day (%)",
        "5",
        validate_percentage
    )
    
    # AI Provider
    print("\n🤖 AI PROVIDER")
    print("-" * 60)
    
    provider = get_input(
        "Provider (9Router)",
        "ninerouter",
        validate_provider
    ).lower()
    
    # 9Router single provider (supports Ollama via 9Router)
    model = get_input(
        "Model (auto untuk auto-routing)",
        "auto",
        lambda x: (True, None)
    )
    
    # Trading Mode
    print("\n🎮 TRADING MODE")
    print("-" * 60)
    
    mode = get_input(
        "Mode (assisted/auto)",
        "assisted",
        validate_mode
    ).lower()
    
    # Summary
    print("\n" + "="*60)
    print("📋 CONFIGURATION SUMMARY")
    print("="*60)
    print(f"Symbol:              {symbol}")
    print(f"Capital:             {capital} USC")
    print(f"Lot Size:            {lot}")
    print(f"Max Trades/Day:      {max_trades}")
    print(f"Confidence:          {confidence}%")
    print(f"Max Drawdown:        {max_drawdown}%")
    print(f"AI Provider:         {provider}")
    print(f"Model:               {model}")
    print(f"Mode:                {mode}")
    print("="*60 + "\n")
    
    confirm = input("Simpan konfigurasi ini? (y/n): ").strip().lower()
    if confirm != 'y':
        print("\n❌ Setup dibatalkan.")
        return
    
    # Build config
    config = {
        'symbol': symbol,
        'lot': float(lot),
        'provider': provider,
        'model': model,
        'mode': mode,
        'max_trades_per_day': int(max_trades),
        'confidence_threshold': int(confidence),
        'max_drawdown_percent': float(max_drawdown),
        'spread_multiplier_limit': 0.3,
        'circuit_breaker_max_errors': 3,
        'circuit_breaker_sleep_hours': 1,
        'atr_sl_multiplier': 1.5,
        'atr_tp_multiplier': 2.5,
        'atr_trailing_multiplier': 1.0,
        'breakeven_after_atr': 1.0,
        'time_exit_minutes': 20,
        'time_exit_min_profit_atr': 0.5,
        'magic_number': 99999,
        'max_deviation': 10,
        'db_path': 'db/sqlite.db',
    }
    
    if provider == 'ninerouter':
        config['ninerouter_url'] = 'http://localhost:20128/v1'
        config['ninerouter_api_key'] = None
    else:
        pass  # fallback ke default 9Router
    
    # Save config
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("\n✅ Konfigurasi berhasil disimpan ke config.yaml")
    print("\n🚀 Next steps:")
    print("   1. Pastikan MT5 sudah running")
    print("   2. Jalankan: 9router")
    print("   3. Jalankan: python trade.py start")
    print("\nHappy Trading! 🎯\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup dibatalkan oleh user.")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
