"""
Background workers untuk TUI trading agent.
Menjalankan data fetching dan AI decision secara async.
"""
import asyncio
from textual.worker import Worker, get_current_worker


async def fetch_market_data(agent):
    """Worker untuk update market data tiap 60 detik"""
    worker = get_current_worker()
    while not worker.is_cancelled:
        try:
            await agent.data_gathering()
            context = await agent.market.get_context()
            yield context
        except Exception as e:
            print(f"[WORKER] Market data error: {e}")
        await asyncio.sleep(60)


async def check_signals(agent):
    """Worker untuk cek sinyal AI tiap tutup candle M5 (5 menit)"""
    worker = get_current_worker()
    while not worker.is_cancelled:
        try:
            if not agent.last_decision:
                decision = await agent.ai.decide(agent.last_context or {})
                agent.last_decision = decision
                yield decision
        except Exception as e:
            print(f"[WORKER] Signal check error: {e}")
        await asyncio.sleep(300)  # 5 menit


async def monitor_positions(agent):
    """Worker untuk monitor posisi tiap 60 detik"""
    worker = get_current_worker()
    while not worker.is_cancelled:
        try:
            await agent.executor.monitor_positions(agent.market.current_atr)
            positions = await agent.executor.get_open_positions()
            yield positions
        except Exception as e:
            print(f"[WORKER] Position monitor error: {e}")
        await asyncio.sleep(60)


async def update_account_info(agent):
    """Worker untuk update info akun tiap 30 detik"""
    import MetaTrader5 as mt5
    worker = get_current_worker()
    while not worker.is_cancelled:
        try:
            if mt5.terminal_info():
                account = mt5.account_info()
                if account:
                    yield {
                        "balance": account.balance,
                        "equity": account.equity,
                        "profit": account.profit,
                    }
        except Exception as e:
            print(f"[WORKER] Account info error: {e}")
        await asyncio.sleep(30)
