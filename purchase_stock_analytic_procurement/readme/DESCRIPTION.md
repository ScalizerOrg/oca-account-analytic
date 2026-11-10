When a buy rule creates a purchase order line (replenishment of a product
supplied on order, without purchase request), this module copies on the line
the analytic distribution of the stock move at the origin of the need (set by
*Stock Analytic*, for instance from a manufacturing order with *MRP Stock
Analytic*).

A procurement is only merged into an existing purchase order line having the
same analytic distribution, so the analytic distribution of a need is never
lost in the line of another one. A need without analytic distribution keeps the
standard behavior.
