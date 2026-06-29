import datetime
import random
import json
from dataclasses import dataclass
from typing import List, Dict

# ==========================================
# 1. MOCK SHOPIFY API (Simulacija)
# ==========================================
class MockShopifyAPI:
    """
    Simulira povlačenje podataka sa Shopify REST/GraphQL API-ja.
    Umjesto pravog requesta, vraća podatke tipične za proizvodnju pića (cider).
    """
    @staticmethod
    def fetch_products() -> List[Dict]:
        return [
            {"id": "PROD_001", "title": "Original Blend Cider - 12 Pack", "inventory_quantity": 450},
            {"id": "PROD_002", "title": "Blackberry Cider - 12 Pack", "inventory_quantity": 120},
            {"id": "PROD_003", "title": "Seasonal Pumpkin Cider - 6 Pack", "inventory_quantity": 85}
        ]

    @staticmethod
    def fetch_recent_orders(days: int = 30) -> List[Dict]:
        orders = []
        now = datetime.datetime.now()
        
        # Generišemo nasumične Shopify narudžbe za proteklih 'days' dana
        for i in range(250):  # 250 narudžbi u zadnjih 30 dana
            order_date = now - datetime.timedelta(days=random.randint(0, days), hours=random.randint(0, 23))
            
            # Nasumičan proizvod, favorizujemo Original Blend (najprodavaniji)
            prod_id = random.choices(
                ["PROD_001", "PROD_002", "PROD_003"], 
                weights=[60, 30, 10], k=1
            )[0]
            
            # Nasumična količina u jednoj narudžbi (1 do 4 paketa)
            qty = random.choices([1, 2, 3, 4], weights=[70, 20, 5, 5], k=1)[0]

            orders.append({
                "order_id": f"ORD_{1000 + i}",
                "product_id": prod_id,
                "quantity": qty,
                "created_at": order_date.isoformat()
            })
        return orders

# ==========================================
# 2. BIZNIS LOGIKA: DEMAND PLANNING & ZALIHE
# ==========================================
@dataclass
class DemandForecastResult:
    product_name: str
    current_stock: int
    sold_last_30d: int
    daily_velocity: float
    reorder_point: int
    suggested_production_qty: int
    needs_reorder: bool

class InventoryPlanner:
    def __init__(self, lead_time_days: int = 7, safety_stock_days: int = 5):
        """
        lead_time_days: Koliko dana treba proizvodnji/dobavljaču da isporuči robu
        safety_stock_days: Koliko dana zaliha držimo kao rezervu ("buffer")
        """
        self.lead_time_days = lead_time_days
        self.safety_stock_days = safety_stock_days
        self.analysis_window_days = 30

    def generate_forecast(self, products: List[Dict], orders: List[Dict]) -> List[DemandForecastResult]:
        forecast_results = []

        # 1. Mapiranje narudžbi na proizvode da nađemo ukupan broj prodanih komada
        sales_data = {p['id']: 0 for p in products}
        for order in orders:
            if order['product_id'] in sales_data:
                sales_data[order['product_id']] += order['quantity']

        # 2. Kalkulacija za svaki proizvod
        for prod in products:
            prod_id = prod['id']
            title = prod['title']
            current_stock = prod['inventory_quantity']
            sold_qty = sales_data.get(prod_id, 0)
            
            # Prosječna dnevna brzina prodaje (Average Daily Velocity)
            daily_velocity = sold_qty / self.analysis_window_days

            # Tačka ponovne narudžbe (Reorder Point = Lead Time Demand + Safety Stock)
            lead_time_demand = daily_velocity * self.lead_time_days
            safety_stock = daily_velocity * self.safety_stock_days
            reorder_point = int(lead_time_demand + safety_stock)

            # Ako zalihe padnu ispod Reorder Point, računamo koliko treba proizvesti
            # Pravilo: Naruči/Proizvedi dovoljno zaliha za narednih 30 dana + Safety stock
            needs_reorder = current_stock <= reorder_point
            
            suggested_qty = 0
            if needs_reorder:
                target_inventory = (daily_velocity * 30) + safety_stock
                suggested_qty = int(target_inventory - current_stock)
                suggested_qty = max(0, suggested_qty) # Sprečava negativne brojeve

            result = DemandForecastResult(
                product_name=title,
                current_stock=current_stock,
                sold_last_30d=sold_qty,
                daily_velocity=round(daily_velocity, 2),
                reorder_point=reorder_point,
                suggested_production_qty=suggested_qty,
                needs_reorder=needs_reorder
            )
            forecast_results.append(result)

        return forecast_results

# ==========================================
# 3. GLAVNA IZVRŠNA BLOKADA (Terminal Output)
# ==========================================
def main():
    print("🚀 Povezivanje na Shopify API (Mock)...")
    products = MockShopifyAPI.fetch_products()
    orders = MockShopifyAPI.fetch_recent_orders(days=30)
    
    print(f"📦 Preuzeto: {len(products)} proizvoda, {len(orders)} narudžbi (zadnjih 30 dana)\n")
    
    # Inicijalizacija Planera (proizvodnji treba 7 dana da skuha cider, želimo 5 dana rezerve)
    planner = InventoryPlanner(lead_time_days=7, safety_stock_days=5)
    report = planner.generate_forecast(products, orders)

    # Crtanje CLI Tabele
    print("-" * 115)
    print(f"{'PRODUCT (SKU)'.ljust(35)} | {'IN STOCK'.ljust(10)} | {'30d SALES'.ljust(10)} | {'VELOCITY'.ljust(10)} | {'REORDER POINT'.ljust(15)} | {'ACTION SUGGESTED'}")
    print("-" * 115)

    for item in report:
        action = f"⚠️ BATCH {item.suggested_production_qty} units" if item.needs_reorder else "✅ HEALTHY"
        row = (
            f"{item.product_name.ljust(35)} | "
            f"{str(item.current_stock).ljust(10)} | "
            f"{str(item.sold_last_30d).ljust(10)} | "
            f"{str(item.daily_velocity).ljust(10)} | "
            f"{str(item.reorder_point).ljust(15)} | "
            f"{action}"
        )
        print(row)
    print("-" * 115)

if __name__ == "__main__":
    main()