USE weight;

-- Clear existing test data if needed
-- DELETE FROM transactions WHERE truck IN ('T-12345', 'T-67890');

-- Insert test data
INSERT INTO transactions (datetime, direction, truck, containers, bruto, neto, produce) 
VALUES
('2025-05-17 10:00:00', 'in', 'T-12345', 'C001,C002', 5000, NULL, 'orange'),
('2025-05-17 15:30:00', 'out', 'T-12345', 'C001,C002', 1500, 3000, 'orange'),
('2025-05-18 09:15:00', 'in', 'T-67890', 'C003', 4800, NULL, 'tomato'),
('2025-05-18 11:45:00', 'none', 'na', 'C004', 500, 500, 'na');