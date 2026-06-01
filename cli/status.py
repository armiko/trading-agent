"""
CLI command: trade status
Cek koneksi MT5, tampilkan balance & equity
"""
import MetaTrader5 as mt5
import sys


def check_mt5_connection() -> bool:
    """Cek apakah MT5 terhubung"""
    if not mt5.initialize():
        print("[ERROR] MT5 initialization failed")
        print(f"Error code: {mt5.last_error()}")
        return False
    return True


def get_account_info():
    """Ambil info akun dari MT5"""
    if not check_mt5_connection():
        return None

    account = mt5.account_info()
    if account is None:
        print("[ERROR] Failed to get account info")
        return None

    return {
        "login": account.login,
        "balance": account.balance,
        "equity": account.equity,
        "profit": account.profit,
        "margin": account.margin,
        "margin_free": account.margin_free,
        "currency": account.currency,
    }


def run_status():
    """Entry point untuk 'trade status'"""
    print("\n=== MT5 CONNECTION STATUS ===")

    info = get_account_info()
    if not info:
        sys.exit(1)

    print(f"\nAccount Login: {info['login']}")
    print(f"Currency: {info['currency']}")
    print(f"Balance: {info['balance']:.2f}")
    print(f"Equity: {info['equity']:.2f}")
    print(f"Profit: {info['profit']:.2f}")
    print(f"Margin: {info['margin']:.2f}")
    print(f"Free Margin: {info['margin_free']:.2f}")

    # Cek posisi terbuka
    positions = mt5.positions_total()
    print(f"\nOpen Positions: {positions}")

    print("\n[OK] MT5 connected successfully\n")
    mt5.shutdown()


if __name__ == "__main__":
    run_status()
