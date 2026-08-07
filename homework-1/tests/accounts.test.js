const request = require('supertest');
const app = require('../src/index');
const { clearTransactions } = require('../src/models/store');

beforeEach(() => {
  clearTransactions();
});

describe('GET /accounts/:accountId/balance', () => {
  test('returns correct per-currency balance after deposits and transfers', async () => {
    await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 500, currency: 'USD', type: 'deposit',
    });
    await request(app).post('/transactions').send({
      fromAccount: 'ACC-12345', toAccount: 'ACC-67890', amount: 200, currency: 'USD', type: 'transfer',
    });
    await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 100, currency: 'EUR', type: 'deposit',
    });

    const res = await request(app).get('/accounts/ACC-12345/balance');
    expect(res.status).toBe(200);
    expect(res.body.accountId).toBe('ACC-12345');
    expect(res.body.balances.USD).toBe(300);
    expect(res.body.balances.EUR).toBe(100);
  });

  test('returns empty balances for unknown account', async () => {
    const res = await request(app).get('/accounts/ACC-99999/balance');
    expect(res.status).toBe(200);
    expect(res.body.accountId).toBe('ACC-99999');
    expect(res.body.balances).toEqual({});
  });

  test('correctly handles withdrawal balance deduction', async () => {
    await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 1000, currency: 'USD', type: 'deposit',
    });
    await request(app).post('/transactions').send({
      fromAccount: 'ACC-12345', amount: 300, currency: 'USD', type: 'withdrawal',
    });

    const res = await request(app).get('/accounts/ACC-12345/balance');
    expect(res.body.balances.USD).toBe(700);
  });
});

describe('GET /accounts/:accountId/summary', () => {
  test('returns correct summary with deposits and withdrawals', async () => {
    await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 500, currency: 'USD', type: 'deposit',
    });
    await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 300, currency: 'USD', type: 'deposit',
    });
    await request(app).post('/transactions').send({
      fromAccount: 'ACC-12345', amount: 200, currency: 'USD', type: 'withdrawal',
    });

    const res = await request(app).get('/accounts/ACC-12345/summary');
    expect(res.status).toBe(200);
    expect(res.body.accountId).toBe('ACC-12345');
    expect(res.body.totalDeposits).toBe(800);
    expect(res.body.totalWithdrawals).toBe(200);
    expect(res.body.transactionCount).toBe(3);
    expect(res.body.mostRecentTransaction).toBeTruthy();
  });

  test('returns zeroes and null for unknown account', async () => {
    const res = await request(app).get('/accounts/ACC-99999/summary');
    expect(res.status).toBe(200);
    expect(res.body.totalDeposits).toBe(0);
    expect(res.body.totalWithdrawals).toBe(0);
    expect(res.body.transactionCount).toBe(0);
    expect(res.body.mostRecentTransaction).toBeNull();
  });
});
