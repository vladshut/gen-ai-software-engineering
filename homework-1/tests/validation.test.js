const { validateTransaction } = require('../src/validators/transactionValidator');

describe('validateTransaction', () => {
  test('accepts a valid transfer', () => {
    const result = validateTransaction({
      fromAccount: 'ACC-12345', toAccount: 'ACC-67890',
      amount: 100.50, currency: 'USD', type: 'transfer',
    });
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  test('rejects negative amount', () => {
    const result = validateTransaction({
      toAccount: 'ACC-12345', amount: -50, currency: 'USD', type: 'deposit',
    });
    expect(result.valid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ field: 'amount', message: 'Amount must be a positive number' })
    );
  });

  test('rejects zero amount', () => {
    const result = validateTransaction({
      toAccount: 'ACC-12345', amount: 0, currency: 'USD', type: 'deposit',
    });
    expect(result.valid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ field: 'amount' })
    );
  });

  test('rejects amount with 3 decimal places', () => {
    const result = validateTransaction({
      toAccount: 'ACC-12345', amount: 100.999, currency: 'USD', type: 'deposit',
    });
    expect(result.valid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ field: 'amount', message: 'Amount must have at most 2 decimal places' })
    );
  });

  test('accepts valid ACC-XXXXX format', () => {
    const result = validateTransaction({
      fromAccount: 'ACC-Ab1Z9', toAccount: 'ACC-12345',
      amount: 10, currency: 'USD', type: 'transfer',
    });
    expect(result.valid).toBe(true);
  });

  test('rejects invalid account format', () => {
    const result = validateTransaction({
      fromAccount: 'INVALID', toAccount: 'ACC-12345',
      amount: 10, currency: 'USD', type: 'transfer',
    });
    expect(result.valid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ field: 'fromAccount' })
    );
  });

  test('accepts valid currency code', () => {
    const result = validateTransaction({
      toAccount: 'ACC-12345', amount: 10, currency: 'EUR', type: 'deposit',
    });
    expect(result.valid).toBe(true);
  });

  test('rejects invalid currency code', () => {
    const result = validateTransaction({
      toAccount: 'ACC-12345', amount: 10, currency: 'XYZ', type: 'deposit',
    });
    expect(result.valid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ field: 'currency', message: 'Invalid currency code' })
    );
  });

  test('accepts valid transaction type', () => {
    const result = validateTransaction({
      fromAccount: 'ACC-12345', amount: 10, currency: 'USD', type: 'withdrawal',
    });
    expect(result.valid).toBe(true);
  });

  test('rejects invalid transaction type', () => {
    const result = validateTransaction({
      toAccount: 'ACC-12345', amount: 10, currency: 'USD', type: 'invalid',
    });
    expect(result.valid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ field: 'type' })
    );
  });

  test('rejects missing fromAccount for transfer', () => {
    const result = validateTransaction({
      toAccount: 'ACC-12345', amount: 10, currency: 'USD', type: 'transfer',
    });
    expect(result.valid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ field: 'fromAccount', message: 'fromAccount is required for this transaction type' })
    );
  });

  test('rejects missing toAccount for deposit', () => {
    const result = validateTransaction({
      amount: 10, currency: 'USD', type: 'deposit',
    });
    expect(result.valid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ field: 'toAccount', message: 'toAccount is required for this transaction type' })
    );
  });

  test('returns multiple errors for multiple invalid fields', () => {
    const result = validateTransaction({
      fromAccount: 'BAD', amount: -5, currency: 'FAKE', type: 'invalid',
    });
    expect(result.valid).toBe(false);
    expect(result.errors.length).toBeGreaterThanOrEqual(3);
  });
});
