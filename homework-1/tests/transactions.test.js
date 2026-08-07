const request = require('supertest');
const app = require('../src/index');
const { clearTransactions } = require('../src/models/store');

beforeEach(() => {
  clearTransactions();
});

describe('POST /transactions', () => {
  test('creates a valid transfer and returns 201', async () => {
    const res = await request(app)
      .post('/transactions')
      .send({
        fromAccount: 'ACC-12345',
        toAccount: 'ACC-67890',
        amount: 100.50,
        currency: 'USD',
        type: 'transfer',
      });

    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('id');
    expect(res.body).toHaveProperty('timestamp');
    expect(res.body.status).toBe('completed');
    expect(res.body.amount).toBe(100.50);
    expect(res.body.currency).toBe('USD');
    expect(res.body.type).toBe('transfer');
  });

  test('creates a valid deposit (no fromAccount) and returns 201', async () => {
    const res = await request(app)
      .post('/transactions')
      .send({
        toAccount: 'ACC-12345',
        amount: 500,
        currency: 'EUR',
        type: 'deposit',
      });

    expect(res.status).toBe(201);
    expect(res.body.fromAccount).toBeNull();
    expect(res.body.toAccount).toBe('ACC-12345');
  });

  test('returns 400 with validation errors for invalid data', async () => {
    const res = await request(app)
      .post('/transactions')
      .send({
        fromAccount: 'INVALID',
        amount: -50,
        currency: 'XYZ',
        type: 'invalid',
      });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Validation failed');
    expect(res.body.details).toBeInstanceOf(Array);
    expect(res.body.details.length).toBeGreaterThan(1);
  });
});

describe('GET /transactions', () => {
  test('returns empty array when no transactions', async () => {
    const res = await request(app).get('/transactions');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  test('returns all transactions', async () => {
    await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 100, currency: 'USD', type: 'deposit',
    });
    await request(app).post('/transactions').send({
      fromAccount: 'ACC-12345', toAccount: 'ACC-67890', amount: 50, currency: 'USD', type: 'transfer',
    });

    const res = await request(app).get('/transactions');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  test('filters by accountId', async () => {
    await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 100, currency: 'USD', type: 'deposit',
    });
    await request(app).post('/transactions').send({
      toAccount: 'ACC-67890', amount: 200, currency: 'USD', type: 'deposit',
    });

    const res = await request(app).get('/transactions?accountId=ACC-12345');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].toAccount).toBe('ACC-12345');
  });

  test('filters by type', async () => {
    await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 100, currency: 'USD', type: 'deposit',
    });
    await request(app).post('/transactions').send({
      fromAccount: 'ACC-12345', amount: 50, currency: 'USD', type: 'withdrawal',
    });

    const res = await request(app).get('/transactions?type=deposit');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].type).toBe('deposit');
  });

  test('filters by date range', async () => {
    await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 100, currency: 'USD', type: 'deposit',
    });

    const res = await request(app).get('/transactions?from=2020-01-01&to=2030-12-31');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
  });
});

describe('GET /transactions/:id', () => {
  test('returns a transaction by id', async () => {
    const created = await request(app).post('/transactions').send({
      toAccount: 'ACC-12345', amount: 100, currency: 'USD', type: 'deposit',
    });

    const res = await request(app).get(`/transactions/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(created.body.id);
  });

  test('returns 404 for nonexistent id', async () => {
    const res = await request(app).get('/transactions/nonexistent-id');
    expect(res.status).toBe(404);
    expect(res.body.error).toBe('Transaction not found');
  });
});

describe('GET /transactions/export', () => {
  test('returns CSV with correct headers', async () => {
    await request(app).post('/transactions').send({
      fromAccount: 'ACC-12345', toAccount: 'ACC-67890', amount: 100, currency: 'USD', type: 'transfer',
    });

    const res = await request(app).get('/transactions/export?format=csv');
    expect(res.status).toBe(200);
    expect(res.headers['content-type']).toContain('text/csv');
    expect(res.text).toContain('id,fromAccount,toAccount,amount,currency,type,timestamp,status');
    expect(res.text.split('\n')).toHaveLength(2);
  });

  test('returns CSV with only headers when no transactions', async () => {
    const res = await request(app).get('/transactions/export?format=csv');
    expect(res.status).toBe(200);
    expect(res.text).toBe('id,fromAccount,toAccount,amount,currency,type,timestamp,status');
  });
});
