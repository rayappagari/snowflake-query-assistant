from skills.base import Skill

skill = Skill(
    name="inventory_analysis",
    description="Inventory levels, stock turnover, and supply chain analysis",
    keywords=[
        "inventory", "stock", "warehouse", "supply", "reorder", "turnover",
        "sku", "units", "stockout", "overstock", "days of supply",
        "out of stock", "low stock", "slow moving", "fast moving",
    ],
    prompt_hint=(
        "This is an inventory/supply chain analysis. "
        "Highlight stockout risks (low inventory relative to demand), "
        "overstock situations, and slow-moving SKUs. "
        "Calculate turnover rate where possible (sales / average inventory). "
        "Flag items below reorder threshold."
    ),
    sql_hint=(
        "-- Inventory analysis patterns:\n"
        "-- Turnover rate: SUM(units_sold) / NULLIF(AVG(inventory_level), 0)\n"
        "-- Days of supply: AVG(inventory_level) / NULLIF(AVG(daily_sales), 0)\n"
        "-- Reorder alert:  CASE WHEN inventory < reorder_point THEN 'reorder' END\n"
        "-- Join sales to inventory: JOIN sales ON inventory.sku = sales.sku"
    ),
)
