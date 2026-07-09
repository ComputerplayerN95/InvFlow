"""
InvFlow 7.1.2/7.1.3 增量升级测试
使用 unittest.mock Mock SQLAlchemy Session
"""

from unittest.mock import MagicMock, patch, PropertyMock, call
import pytest
from datetime import datetime
from decimal import Decimal
from typing import List, Dict


# ====================================================================
#  辅助函数 & Fixtures
# ====================================================================

@pytest.fixture
def mock_db():
    """创建一个 MagicMock SQLAlchemy Session"""
    db = MagicMock()
    db.commit.return_value = None
    db.flush.return_value = None
    db.refresh.return_value = None
    return db


@pytest.fixture
def now():
    return datetime(2026, 7, 9, 10, 0, 0)


def make_batch_stock(**kwargs):
    """创建 BatchStock mock 对象"""
    bs = MagicMock()
    bs.BatchID = kwargs.get("BatchID", "BT20260709100000101")
    bs.ProductID = kwargs.get("ProductID", "P001")
    bs.WarehouseID = kwargs.get("WarehouseID", "WH01")
    bs.PurchaseDetailID = kwargs.get("PurchaseDetailID", "PD001")
    bs.Quantity = kwargs.get("Quantity", 100)
    bs.RemainingQty = kwargs.get("RemainingQty", 100)
    bs.UnitPrice = kwargs.get("UnitPrice", Decimal("10.00"))
    bs.InDate = kwargs.get("InDate", datetime(2026, 1, 1, 8, 0, 0))
    return bs


def mock_batch_query(mock_db, batches, product_id="P001", warehouse_id="WH01"):
    """配置 mock_db 的 query().filter().order_by().all() 链返回指定批次"""
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.order_by.return_value.all.return_value = batches
    query_mock.filter.return_value = filter_mock
    mock_db.query.return_value = query_mock
    return query_mock, filter_mock


# ====================================================================
#  P0: FIFO 成本核算
# ====================================================================

class TestFIFODeductWithDetail:
    """测试 fifo_deduct_with_detail 函数"""

    def test_normal_deduct_from_earliest_batch(self, mock_db):
        """正常FIFO扣减：从最早批次扣"""
        early = make_batch_stock(
            BatchID="BT20260101001", InDate=datetime(2026, 1, 1),
            RemainingQty=50, UnitPrice=Decimal("10.00")
        )
        late = make_batch_stock(
            BatchID="BT20260201001", InDate=datetime(2026, 2, 1),
            RemainingQty=50, UnitPrice=Decimal("12.00")
        )
        mock_batch_query(mock_db, [early, late])

        from app.utils.stock_utils import fifo_deduct_with_detail

        result = fifo_deduct_with_detail(mock_db, "P001", "WH01", 30)

        assert len(result) == 1
        assert result[0]["BatchID"] == "BT20260101001"
        assert result[0]["Quantity"] == 30
        assert result[0]["UnitPrice"] == 10.0
        assert early.RemainingQty == 20  # 50-30
        assert late.RemainingQty == 50  # 未动

    def test_deduct_across_batches(self, mock_db):
        """跨批次扣减：一个批次不够扣下一个"""
        batch1 = make_batch_stock(
            BatchID="BT20260101001", InDate=datetime(2026, 1, 1),
            RemainingQty=30, UnitPrice=Decimal("10.00")
        )
        batch2 = make_batch_stock(
            BatchID="BT20260201001", InDate=datetime(2026, 2, 1),
            RemainingQty=50, UnitPrice=Decimal("12.00")
        )
        mock_batch_query(mock_db, [batch1, batch2])

        from app.utils.stock_utils import fifo_deduct_with_detail

        result = fifo_deduct_with_detail(mock_db, "P001", "WH01", 60)

        assert len(result) == 2
        assert result[0]["BatchID"] == "BT20260101001"
        assert result[0]["Quantity"] == 30
        assert result[1]["BatchID"] == "BT20260201001"
        assert result[1]["Quantity"] == 30
        assert batch1.RemainingQty == 0  # 扣完
        assert batch2.RemainingQty == 20  # 50-30

    def test_exact_match_one_batch(self, mock_db):
        """精确匹配一个批次"""
        batch = make_batch_stock(
            BatchID="BT20260101001", RemainingQty=50, UnitPrice=Decimal("10.00")
        )
        mock_batch_query(mock_db, [batch])

        from app.utils.stock_utils import fifo_deduct_with_detail

        result = fifo_deduct_with_detail(mock_db, "P001", "WH01", 50)

        assert len(result) == 1
        assert result[0]["Quantity"] == 50
        assert batch.RemainingQty == 0

    def test_insufficient_stock(self, mock_db):
        """超出库存量：应返回扣减明细，但剩余部分无法扣减"""
        batch = make_batch_stock(
            BatchID="BT20260101001", RemainingQty=50, UnitPrice=Decimal("10.00")
        )
        mock_batch_query(mock_db, [batch])

        from app.utils.stock_utils import fifo_deduct_with_detail

        result = fifo_deduct_with_detail(mock_db, "P001", "WH01", 100)

        # 只扣到库存用完
        assert len(result) == 1
        assert result[0]["Quantity"] == 50
        assert batch.RemainingQty == 0
        # 注意：函数扣完后不管剩余，不会抛异常

    def test_no_batches(self, mock_db):
        """没有可用批次时返回空列表"""
        mock_batch_query(mock_db, [])

        from app.utils.stock_utils import fifo_deduct_with_detail

        result = fifo_deduct_with_detail(mock_db, "P001", "WH01", 10)

        assert result == []

    def test_zero_quantity(self, mock_db):
        """扣减0数量"""
        batch = make_batch_stock(BatchID="BT20260101001", RemainingQty=50)
        mock_batch_query(mock_db, [batch])

        from app.utils.stock_utils import fifo_deduct_with_detail

        result = fifo_deduct_with_detail(mock_db, "P001", "WH01", 0)

        assert len(result) == 0
        assert batch.RemainingQty == 50


class TestFIFODeduct:
    """测试 fifo_deduct 函数（无返回明细版本）"""

    def test_fifo_deduct_from_earliest(self, mock_db):
        """正常FIFO扣减"""
        early = make_batch_stock(
            BatchID="BT20260101001", InDate=datetime(2026, 1, 1),
            RemainingQty=50, UnitPrice=Decimal("10.00")
        )
        late = make_batch_stock(
            BatchID="BT20260201001", InDate=datetime(2026, 2, 1),
            RemainingQty=50, UnitPrice=Decimal("12.00")
        )
        mock_batch_query(mock_db, [early, late])

        from app.utils.stock_utils import fifo_deduct

        result = fifo_deduct(mock_db, "P001", "WH01", 30)

        assert result is None  # 无返回值
        assert early.RemainingQty == 20
        assert late.RemainingQty == 50

    def test_fifo_deduct_across_batches(self, mock_db):
        """跨批次扣减"""
        batch1 = make_batch_stock(BatchID="BT1", RemainingQty=30)
        batch2 = make_batch_stock(BatchID="BT2", RemainingQty=50)
        mock_batch_query(mock_db, [batch1, batch2])

        from app.utils.stock_utils import fifo_deduct

        fifo_deduct(mock_db, "P001", "WH01", 60)

        assert batch1.RemainingQty == 0
        assert batch2.RemainingQty == 20


# ====================================================================
#  P1: 采购退货函数
# ====================================================================

class TestApplyPurchaseReturn:
    """测试 apply_purchase_return"""

    def _setup_purchase_return_mocks(self, mock_db, batch, ws, ts):
        """统一设置 apply_purchase_return 的三个 query mock"""
        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else ''
            if 'BatchStock' in mn:
                f = MagicMock()
                f.order_by.return_value.all.return_value = [batch]
                q.filter.return_value = f
            elif 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = ws
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = ts
            return q
        mock_db.query.side_effect = query_side_effect

    def test_deduct_by_purchase_detail_id(self, mock_db, now):
        """按 PurchaseDetailID 精确扣减 BatchStock"""
        batch = make_batch_stock(
            BatchID="BT001", PurchaseDetailID="PD001",
            RemainingQty=100, UnitPrice=Decimal("10.00")
        )
        ws = MagicMock()
        ws.Quantity = 100
        ts = MagicMock()
        ts.TotalQuantity = 100
        self._setup_purchase_return_mocks(mock_db, batch, ws, ts)

        from app.utils.stock_utils import apply_purchase_return

        details = [{"PurchaseDetailID": "PD001", "ProductID": "P001",
                     "Quantity": 30, "UnitPrice": 10.0}]
        apply_purchase_return(mock_db, "WH01", details, now)

        assert batch.RemainingQty == 70  # 100-30
        assert ws.Quantity == 70  # 100-30
        assert ts.TotalQuantity == 70  # 100-30

    def test_partial_return(self, mock_db, now):
        """部分退货"""
        batch = make_batch_stock(
            BatchID="BT001", PurchaseDetailID="PD001",
            RemainingQty=100
        )
        ws = MagicMock()
        ws.Quantity = 200
        ts = MagicMock()
        ts.TotalQuantity = 200
        self._setup_purchase_return_mocks(mock_db, batch, ws, ts)

        from app.utils.stock_utils import apply_purchase_return

        details = [{"PurchaseDetailID": "PD001", "ProductID": "P001",
                     "Quantity": 10, "UnitPrice": 10.0}]
        apply_purchase_return(mock_db, "WH01", details, now)

        assert batch.RemainingQty == 90
        assert ws.Quantity == 190
        assert ts.TotalQuantity == 190

    def test_full_return(self, mock_db, now):
        """全量退货"""
        batch = make_batch_stock(
            BatchID="BT001", PurchaseDetailID="PD001",
            RemainingQty=50
        )
        ws = MagicMock()
        ws.Quantity = 50
        ts = MagicMock()
        ts.TotalQuantity = 50
        self._setup_purchase_return_mocks(mock_db, batch, ws, ts)

        from app.utils.stock_utils import apply_purchase_return

        details = [{"PurchaseDetailID": "PD001", "ProductID": "P001",
                     "Quantity": 50, "UnitPrice": 10.0}]
        apply_purchase_return(mock_db, "WH01", details, now)

        assert batch.RemainingQty == 0
        assert ws.Quantity == 0
        assert ts.TotalQuantity == 0

    def test_no_warehouse_stock_record(self, mock_db, now):
        """WarehouseStock 不存在时不应报错"""
        batch = make_batch_stock(BatchID="BT001", RemainingQty=100)
        self._setup_purchase_return_mocks(mock_db, batch, None, None)

        from app.utils.stock_utils import apply_purchase_return

        details = [{"PurchaseDetailID": "PD001", "ProductID": "P001",
                     "Quantity": 10, "UnitPrice": 10.0}]

        # 不应抛出异常
        apply_purchase_return(mock_db, "WH01", details, now)


class TestRollbackPurchaseReturn:
    """测试 rollback_purchase_return"""

    def test_restore_batch_stock(self, mock_db, now):
        """恢复 BatchStock"""
        batch = make_batch_stock(
            BatchID="BT001", PurchaseDetailID="PD001",
            Quantity=100, RemainingQty=70, UnitPrice=Decimal("10.00")
        )
        ws = MagicMock()
        ws.Quantity = 70
        ts = MagicMock()
        ts.TotalQuantity = 70

        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else ''
            if 'BatchStock' in mn:
                f = MagicMock()
                f.order_by.return_value.all.return_value = [batch]
                q.filter.return_value = f
            elif 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = ws
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = ts
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import rollback_purchase_return

        details = [{"PurchaseDetailID": "PD001", "ProductID": "P001",
                     "Quantity": 30, "UnitPrice": 10.0}]
        rollback_purchase_return(mock_db, "RET001", "WH01", details, now)

        # 恢复到原来的 RemainingQty（100-30=70 → 70+30=100）
        assert batch.RemainingQty == 100
        assert ws.Quantity == 100
        assert ts.TotalQuantity == 100

    def test_restore_with_new_batch(self, mock_db, now):
        """批次已满，创建新批次"""
        batch = make_batch_stock(
            BatchID="BT001", PurchaseDetailID="PD001",
            Quantity=100, RemainingQty=100, UnitPrice=Decimal("10.00")
        )
        ws = MagicMock()
        ws.Quantity = 70
        ts = MagicMock()
        ts.TotalQuantity = 70

        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else ''
            if 'BatchStock' in mn:
                f = MagicMock()
                f.order_by.return_value.all.return_value = [batch]
                q.filter.return_value = f
            elif 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = ws
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = ts
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import rollback_purchase_return

        details = [{"PurchaseDetailID": "PD002", "ProductID": "P001",
                     "Quantity": 30, "UnitPrice": 10.0}]
        rollback_purchase_return(mock_db, "RET001", "WH01", details, now)

        # 新批次被创建
        assert mock_db.add.called
        assert ws.Quantity == 100
        assert ts.TotalQuantity == 100

    def test_no_warehouse_stock_record_creates_new(self, mock_db, now):
        """WarehouseStock 不存在时创建新的"""
        batch = make_batch_stock(BatchID="BT001", RemainingQty=50)

        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else ''
            if 'BatchStock' in mn:
                f = MagicMock()
                f.order_by.return_value.all.return_value = [batch]
                q.filter.return_value = f
            elif 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = None
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = None
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import rollback_purchase_return

        details = [{"PurchaseDetailID": "PD001", "ProductID": "P001",
                     "Quantity": 10, "UnitPrice": 10.0}]
        rollback_purchase_return(mock_db, "RET001", "WH01", details, now)

        # 确保创建了新的 WarehouseStock 和 TotalStock
        assert mock_db.add.called


# ====================================================================
#  P1: 销售退货函数
# ====================================================================

class TestApplySaleReturn:
    """测试 apply_sale_return"""

    def test_restore_by_sale_out_batch(self, mock_db, now):
        """按 SaleOutBatch 原路恢复 BatchStock"""
        sob = MagicMock()
        sob.SaleOutBatchID = "SOB001"
        sob.SaleDetailID = "SD001"
        sob.BatchID = "BT001"
        sob.Quantity = 30
        sob.UnitPrice = 10.0
        sob.OutDate = datetime(2026, 6, 1)

        batch = make_batch_stock(
            BatchID="BT001", Quantity=100, RemainingQty=70,
            UnitPrice=Decimal("10.00")
        )

        ws = MagicMock()
        ws.Quantity = 70
        ts = MagicMock()
        ts.TotalQuantity = 70

        # Mock SaleOutBatch query
        sob_query = MagicMock()
        sob_filter = MagicMock()
        sob_filter.order_by.return_value.all.return_value = [sob]
        sob_query.filter.return_value = sob_filter

        # Mock BatchStock query for single batch lookup
        batch_query = MagicMock()
        batch_filter = MagicMock()
        batch_filter.first.return_value = batch
        batch_query.filter.return_value = batch_filter

        # Mock WarehouseStock and TotalStock
        ws_query = MagicMock()
        ws_filter = MagicMock()
        ws_filter.first.return_value = ws
        ws_query.filter.return_value = ws_filter

        ts_query = MagicMock()
        ts_filter = MagicMock()
        ts_filter.first.return_value = ts
        ts_query.filter.return_value = ts_filter

        call_count = [0]

        def query_side_effect(model):
            call_count[0] += 1
            q = MagicMock()
            model_name = model.__name__ if hasattr(model, '__name__') else str(model)

            if 'SaleOutBatch' in model_name:
                return sob_query
            elif 'BatchStock' in model_name:
                return batch_query
            elif 'WarehouseStock' in model_name:
                return ws_query
            elif 'TotalStock' in model_name:
                return ts_query
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import apply_sale_return

        details = [{"SaleDetailID": "SD001", "ProductID": "P001",
                     "Quantity": 30, "UnitPrice": 10.0}]

        apply_sale_return(mock_db, "WH01", details, now)

        # RemainingQty 恢复到 100
        assert batch.RemainingQty == 100
        assert ws.Quantity == 100
        assert ts.TotalQuantity == 100

    def test_all_batches_full_creates_new(self, mock_db, now):
        """所有批次都满了，创建新批次"""
        sob = MagicMock()
        sob.SaleDetailID = "SD001"
        sob.BatchID = "BT001"
        sob.Quantity = 30

        batch = make_batch_stock(
            BatchID="BT001", Quantity=100, RemainingQty=100
        )

        ws = MagicMock()
        ws.Quantity = 100
        ts = MagicMock()
        ts.TotalQuantity = 100

        sob_query = MagicMock()
        sob_query.filter.return_value.order_by.return_value.all.return_value = [sob]

        batch_filter_for_lookup = MagicMock()
        batch_filter_for_lookup.first.return_value = batch

        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else str(model)
            if 'SaleOutBatch' in mn:
                return sob_query
            elif 'BatchStock' in mn:
                q.filter.return_value = batch_filter_for_lookup
                return q
            elif 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = ws
                return q
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = ts
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import apply_sale_return

        details = [{"SaleDetailID": "SD001", "ProductID": "P001",
                     "Quantity": 30, "UnitPrice": 10.0}]

        apply_sale_return(mock_db, "WH01", details, now)

        # 新批次创建了
        assert mock_db.add.called
        assert batch.RemainingQty == 100  # 原批次不变


class TestRollbackSaleReturn:
    """测试 rollback_sale_return"""

    def test_reverse_deduct(self, mock_db, now):
        """反向扣减 BatchStock"""
        sob = MagicMock()
        sob.SaleDetailID = "SD001"
        sob.BatchID = "BT001"
        sob.Quantity = 30

        batch = make_batch_stock(
            BatchID="BT001", Quantity=100, RemainingQty=100
        )

        ws = MagicMock()
        ws.Quantity = 100
        ts = MagicMock()
        ts.TotalQuantity = 100

        # SaleOutBatch query (desc order)
        sob_query = MagicMock()
        sob_query.filter.return_value.order_by.return_value.all.return_value = [sob]

        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else str(model)
            if 'SaleOutBatch' in mn:
                return sob_query
            elif 'BatchStock' in mn:
                q.filter.return_value.first.return_value = batch
                return q
            elif 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = ws
                return q
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = ts
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import rollback_sale_return

        details = [{"SaleDetailID": "SD001", "ProductID": "P001",
                     "Quantity": 30, "UnitPrice": 10.0}]

        rollback_sale_return(mock_db, "RET001", "WH01", details, now)

        assert batch.RemainingQty == 70  # 100-30
        assert ws.Quantity == 70
        assert ts.TotalQuantity == 70


# ====================================================================
#  P2: 损益库存函数
# ====================================================================

class TestApplyProfitLoss:
    """测试 apply_profit_loss"""

    def test_profit_creates_new_batch_and_increases_stock(self, mock_db, now):
        """盘盈：创建新BatchStock，增加库存"""
        ws = MagicMock()
        ws.Quantity = 100
        ts = MagicMock()
        ts.TotalQuantity = 100
        ts.AveragePrice = 10.0

        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else str(model)
            if 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = ws
                return q
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = ts
                return q
            return q

        # 对于 profit，不查 BatchStock，但需要让第一个 query().filter().order_by().all() 不被触发
        # apply_profit_loss 对盘盈不查 BatchStock，直接 db.add(new_batch)
        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import apply_profit_loss

        details = [{"ProductID": "P001", "Quantity": 50,
                     "UnitPrice": 12.0, "ProfitLossDetailID": "PLD001"}]

        apply_profit_loss(mock_db, "WH01", details, now)

        assert mock_db.add.called  # 新BatchStock被创建
        assert ws.Quantity == 150  # 100+50
        assert ts.TotalQuantity == 150
        # 均价更新: (100*10 + 50*12) / 150 = 1600/150 = 10.67
        assert ts.AveragePrice == 10.67

    def test_profit_new_warehouse_and_total_stock(self, mock_db, now):
        """盘盈：WarehouseStock 和 TotalStock 不存在时创建新的"""
        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else str(model)
            if 'WarehouseStock' in mn or 'TotalStock' in mn:
                q.filter.return_value.first.return_value = None
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import apply_profit_loss

        details = [{"ProductID": "P001", "Quantity": 50,
                     "UnitPrice": 12.0, "ProfitLossDetailID": "PLD001"}]

        apply_profit_loss(mock_db, "WH01", details, now)

        assert mock_db.add.called

    def test_loss_fifo_deduct_and_decreases_stock(self, mock_db, now):
        """盘亏：FIFO扣减BatchStock，减少库存"""
        batch = make_batch_stock(BatchID="BT001", RemainingQty=100, UnitPrice=Decimal("10.00"))

        # FIFO deduct query
        fifo_filter = MagicMock()
        fifo_filter.order_by.return_value.all.return_value = [batch]

        ws = MagicMock()
        ws.Quantity = 100
        ts = MagicMock()
        ts.TotalQuantity = 100

        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else str(model)
            if 'BatchStock' in mn and 'SaleOutBatch' not in mn:
                q.filter.return_value = fifo_filter
                return q
            elif 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = ws
                return q
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = ts
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import apply_profit_loss

        details = [{"ProductID": "P001", "Quantity": -30,
                     "UnitPrice": 0, "ProfitLossDetailID": "PLD002"}]

        apply_profit_loss(mock_db, "WH01", details, now)

        assert batch.RemainingQty == 70  # 100-30
        assert ws.Quantity == 70
        assert ts.TotalQuantity == 70


class TestRollbackProfitLoss:
    """测试 rollback_profit_loss"""

    def test_rollback_profit_deducts(self, mock_db, now):
        """盘盈回退：扣减"""
        batch = make_batch_stock(BatchID="BT001", RemainingQty=50)

        fifo_filter = MagicMock()
        fifo_filter.order_by.return_value.all.return_value = [batch]

        ws = MagicMock()
        ws.Quantity = 150
        ts = MagicMock()
        ts.TotalQuantity = 150
        ts.AveragePrice = 10.67

        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else str(model)
            if 'BatchStock' in mn and 'SaleOutBatch' not in mn:
                q.filter.return_value = fifo_filter
                return q
            elif 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = ws
                return q
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = ts
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import rollback_profit_loss

        details = [{"ProductID": "P001", "Quantity": 50,
                     "UnitPrice": 12.0, "ProfitLossDetailID": "PLD001"}]

        rollback_profit_loss(mock_db, "PL001", "WH01", details, now)

        assert batch.RemainingQty == 0  # 50-50
        assert ws.Quantity == 100  # 150-50
        assert ts.TotalQuantity == 100  # 150-50

    def test_rollback_loss_restores(self, mock_db, now):
        """盘亏回退：恢复（创建新批次，增加库存）"""
        ws = MagicMock()
        ws.Quantity = 70
        ts = MagicMock()
        ts.TotalQuantity = 70
        ts.AveragePrice = 10.0

        def query_side_effect(model):
            q = MagicMock()
            mn = model.__name__ if hasattr(model, '__name__') else str(model)
            if 'WarehouseStock' in mn:
                q.filter.return_value.first.return_value = ws
                return q
            elif 'TotalStock' in mn:
                q.filter.return_value.first.return_value = ts
                return q
            return q

        mock_db.query.side_effect = query_side_effect

        from app.utils.stock_utils import rollback_profit_loss

        details = [{"ProductID": "P001", "Quantity": -30,
                     "UnitPrice": 10.0, "ProfitLossDetailID": "PLD002"}]

        rollback_profit_loss(mock_db, "PL001", "WH01", details, now)

        assert mock_db.add.called  # 新批次被创建
        assert ws.Quantity == 100  # 70+30
        assert ts.TotalQuantity == 100  # 70+30
        assert ts.AveragePrice == 10.0  # (70*10 + 30*10) / 100


# ====================================================================
#  Schema 验证
# ====================================================================

class TestSchemas:
    """验证所有新 Schema 类能被 Pydantic 实例化"""

    def test_purchase_return_schemas(self):
        """采购退货 Schema"""
        from app.schemas import (
            PurchaseReturnDetailItem, PurchaseReturnCreate,
            PurchaseReturnUpdate, PurchaseReturnDetailOut,
            PurchaseReturnOrderOut, PurchaseReturnOrderFullOut,
        )

        item = PurchaseReturnDetailItem(
            ReturnDetailID="RD001", PurchaseDetailID="PD001",
            ProductID="P001", Quantity=10.0, UnitPrice=15.0, Amount=150.0,
        )
        assert item.ReturnDetailID == "RD001"
        assert item.Quantity == 10.0

        create = PurchaseReturnCreate(
            ReturnID="PR001", PurchaseID="PO001",
            SupplierID="S001", WarehouseID="WH01",
            Details=[item],
        )
        assert create.ReturnID == "PR001"
        assert len(create.Details) == 1
        assert create.ReturnDate is None  # Optional

        update = PurchaseReturnUpdate(Operator="张三")
        assert update.Operator == "张三"
        assert update.Details is None  # 未传

    def test_sale_return_schemas(self):
        """销售退货 Schema"""
        from app.schemas import (
            SaleReturnDetailItem, SaleReturnCreate,
            SaleReturnUpdate, SaleReturnDetailOut,
            SaleReturnOrderOut, SaleReturnOrderFullOut,
        )

        item = SaleReturnDetailItem(
            ReturnDetailID="RD001", SaleDetailID="SD001",
            ProductID="P001", Quantity=5.0, UnitPrice=20.0, Amount=100.0,
        )
        assert item.SaleDetailID == "SD001"

        create = SaleReturnCreate(
            ReturnID="SR001", SaleID="SO001",
            CustomerID="C001", WarehouseID="WH01",
        )
        assert create.Details == []  # 默认空列表

    def test_stock_check_schemas(self):
        """盘点单 Schema"""
        from app.schemas import (
            StockCheckDetailItem, StockCheckCreate,
            StockCheckDetailOut, StockCheckOrderOut,
            StockCheckOrderFullOut,
        )

        item = StockCheckDetailItem(
            CheckDetailID="CD001", ProductID="P001",
            BookQuantity=100.0, ActualQuantity=110.0,
        )
        assert item.DiffQuantity == 0  # 默认值
        assert item.UnitPrice == 0  # 默认值

        # DiffQuantity 可手动指定
        item2 = StockCheckDetailItem(
            CheckDetailID="CD002", ProductID="P002",
            BookQuantity=50.0, ActualQuantity=45.0,
            DiffQuantity=-5.0, UnitPrice=10.0,
        )
        assert item2.DiffQuantity == -5.0

        create = StockCheckCreate(
            CheckID="SC001", WarehouseID="WH01",
            Details=[item, item2],
        )
        assert len(create.Details) == 2

    def test_profit_loss_schemas(self):
        """损益单 Schema"""
        from app.schemas import (
            ProfitLossDetailItem, ProfitLossCreate,
            ProfitLossDetailOut, ProfitLossOrderOut,
            ProfitLossOrderFullOut,
        )

        item = ProfitLossDetailItem(
            ProfitLossDetailID="PLD001", ProductID="P001",
            Quantity=50.0, UnitPrice=12.0, Amount=600.0,
        )
        assert item.BatchID is None
        assert item.Remark is None

        create = ProfitLossCreate(
            ProfitLossID="PL001", WarehouseID="WH01",
            Type="盘盈", Details=[item],
        )
        assert create.Type == "盘盈"
        assert create.CheckID is None  # Optional

    def test_fifo_report_schemas(self):
        """FIFO 报表 Schema"""
        from app.schemas import (
            FIFOSalesProfitItem, FIFOSalesProfitReport,
            FIFOCostComparisonItem, FIFOCostComparisonReport,
            SaleOutBatchOut,
        )

        item = FIFOSalesProfitItem(
            ProductID="P001", ProductName="测试商品",
            SaleQty=100.0, SaleAmount=2000.0,
            CostAmount=1500.0, GrossProfit=500.0, ProfitRate=25.0,
        )
        assert item.GrossProfit == 500.0

        report = FIFOSalesProfitReport(year_month="2026-07")
        assert report.report == []

        comp_item = FIFOCostComparisonItem(
            ProductID="P001", SaleQty=100.0,
            FIFOCostAmount=1500.0, AverageCostAmount=1600.0,
        )
        assert comp_item.Difference == 0  # 默认

    def test_message_response_schema(self):
        """通用响应"""
        from app.schemas import MessageResponse
        resp = MessageResponse(message="成功")
        assert resp.success is True
        assert resp.message == "成功"

        resp2 = MessageResponse(message="失败", success=False)
        assert resp2.success is False

    def test_purchase_return_order_out_defaults(self):
        """PurchaseReturnOrderOut 默认值"""
        from app.schemas import PurchaseReturnOrderOut
        o = PurchaseReturnOrderOut(
            ReturnID="PR001", PurchaseID="PO001",
            SupplierID="S001", WarehouseID="WH001",
        )
        assert o.Status == "草稿"
        assert o.TotalAmount == 0
        assert o.ReturnOperator is None

    def test_sale_return_detail_out(self):
        """SaleReturnDetailOut ORM mode"""
        from app.schemas import SaleReturnDetailOut

        # 模拟从 ORM 模型创建
        mock_instance = MagicMock()
        mock_instance.ReturnDetailID = "RD001"
        mock_instance.ReturnID = "SR001"
        mock_instance.SaleDetailID = "SD001"
        mock_instance.ProductID = "P001"
        mock_instance.Quantity = 10.0
        mock_instance.UnitPrice = 20.0
        mock_instance.Amount = 200.0

        out = SaleReturnDetailOut.model_validate(mock_instance)
        assert out.ReturnDetailID == "RD001"
        assert out.Amount == 200.0

    def test_stock_check_detail_out(self):
        """StockCheckDetailOut ORM mode"""
        from app.schemas import StockCheckDetailOut

        mock_instance = MagicMock()
        mock_instance.CheckDetailID = "CD001"
        mock_instance.CheckID = "SC001"
        mock_instance.ProductID = "P001"
        mock_instance.BookQuantity = 100.0
        mock_instance.ActualQuantity = 110.0
        mock_instance.DiffQuantity = 10.0
        mock_instance.UnitPrice = 0
        mock_instance.Remark = None

        out = StockCheckDetailOut.model_validate(mock_instance)
        assert out.DiffQuantity == 10.0


# ====================================================================
#  API 路由验证
# ====================================================================

class TestAPIRoutes:
    """验证路由前缀和端点格式"""

    def test_purchase_return_router_prefix(self):
        """采购退货子路由前缀"""
        from app.routers.returns import purchase_return_router
        assert purchase_return_router.prefix == "/purchase-returns"

    def test_sale_return_router_prefix(self):
        """销售退货子路由前缀"""
        from app.routers.returns import sale_return_router
        assert sale_return_router.prefix == "/sale-returns"

    def test_stock_check_router_prefix(self):
        """盘点单子路由前缀"""
        from app.routers.stock_check import stock_check_router
        assert stock_check_router.prefix == "/stock-checks"

    def test_profit_loss_router_prefix(self):
        """损益单子路由前缀"""
        from app.routers.stock_check import profit_loss_router
        assert profit_loss_router.prefix == "/profit-loss"

    def test_main_return_router_prefix(self):
        """退货管理主路由前缀"""
        from app.routers.returns import router
        assert router.prefix == "/api"

    def test_main_stock_check_router_prefix(self):
        """盘点管理主路由前缀"""
        from app.routers.stock_check import router
        assert router.prefix == "/api"

    def test_purchase_return_endpoints(self):
        """采购退货端点路径格式"""
        from app.routers.returns import purchase_return_router

        paths = [(route.path, list(route.methods)) for route in purchase_return_router.routes]

        expected_paths = [
            ("/purchase-returns/", {"GET"}),
            ("/purchase-returns/", {"POST"}),
            ("/purchase-returns/{return_id}", {"GET"}),
            ("/purchase-returns/{return_id}", {"PUT"}),
            ("/purchase-returns/{return_id}", {"DELETE"}),
            ("/purchase-returns/{return_id}/execute", {"POST"}),
            ("/purchase-returns/{return_id}/rollback", {"POST"}),
        ]

        for expected_path, expected_methods in expected_paths:
            matching = [(p, m) for p, m in paths if p == expected_path]
            assert matching, f"路径 {expected_path} 未找到"
            found_methods = set()
            for p, m in matching:
                found_methods.update(m)
            for method in expected_methods:
                assert method in found_methods, \
                    f"路径 {expected_path} 缺少方法 {method}"

    def test_sale_return_endpoints(self):
        """销售退货端点路径格式"""
        from app.routers.returns import sale_return_router

        paths = [(route.path, list(route.methods)) for route in sale_return_router.routes]

        expected = [
            ("/sale-returns/", "GET"),
            ("/sale-returns/", "POST"),
            ("/sale-returns/{return_id}", "GET"),
            ("/sale-returns/{return_id}", "PUT"),
            ("/sale-returns/{return_id}", "DELETE"),
            ("/sale-returns/{return_id}/execute", "POST"),
            ("/sale-returns/{return_id}/rollback", "POST"),
        ]

        for exp_path, exp_method in expected:
            matching = [(p, m) for p, m in paths if p == exp_path]
            assert matching, f"销售退货路径 {exp_path} 未找到"

    def test_stock_check_endpoints(self):
        """盘点单端点路径格式"""
        from app.routers.stock_check import stock_check_router

        paths = [(route.path, list(route.methods)) for route in stock_check_router.routes]

        expected = [
            ("/stock-checks/", "GET"),
            ("/stock-checks/", "POST"),
            ("/stock-checks/{check_id}", "GET"),
            ("/stock-checks/{check_id}", "PUT"),
            ("/stock-checks/{check_id}", "DELETE"),
            ("/stock-checks/{check_id}/audit", "POST"),
            ("/stock-checks/{check_id}/rollback", "POST"),
        ]

        for exp_path, exp_method in expected:
            matching = [(p, m) for p, m in paths if p == exp_path]
            assert matching, f"盘点单路径 {exp_path} 未找到"

    def test_profit_loss_endpoints(self):
        """损益单端点路径格式"""
        from app.routers.stock_check import profit_loss_router

        paths = [(route.path, list(route.methods)) for route in profit_loss_router.routes]

        expected = [
            ("/profit-loss/", "GET"),
            ("/profit-loss/", "POST"),
            ("/profit-loss/{pl_id}", "GET"),
            ("/profit-loss/{pl_id}", "PUT"),
            ("/profit-loss/{pl_id}", "DELETE"),
            ("/profit-loss/{pl_id}/audit", "POST"),
            ("/profit-loss/{pl_id}/rollback", "POST"),
        ]

        for exp_path, exp_method in expected:
            matching = [(p, m) for p, m in paths if p == exp_path]
            assert matching, f"损益单路径 {exp_path} 未找到"
