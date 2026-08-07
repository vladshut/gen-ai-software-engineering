const express = require('express');
const router = express.Router();
const { addTransaction, getAllTransactions, getTransactionById } = require('../models/store');
const { validateTransaction } = require('../validators/transactionValidator');
const { generateId, generateTimestamp, transactionsToCsv } = require('../utils/helpers');

// GET /transactions/export — must be before /:id to avoid "export" being treated as an ID
router.get('/export', (req, res) => {
  if (req.query.format === 'csv') {
    const transactions = getAllTransactions();
    const csv = transactionsToCsv(transactions);
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename="transactions.csv"');
    return res.status(200).send(csv);
  }
  return res.status(400).json({ error: 'Unsupported export format. Use ?format=csv' });
});

// POST /transactions
router.post('/', (req, res) => {
  const { valid, errors } = validateTransaction(req.body);

  if (!valid) {
    return res.status(400).json({ error: 'Validation failed', details: errors });
  }

  const transaction = {
    id: generateId(),
    fromAccount: req.body.fromAccount || null,
    toAccount: req.body.toAccount || null,
    amount: req.body.amount,
    currency: req.body.currency,
    type: req.body.type,
    timestamp: generateTimestamp(),
    status: 'completed',
  };

  addTransaction(transaction);
  return res.status(201).json(transaction);
});

// GET /transactions
router.get('/', (req, res) => {
  let results = getAllTransactions();

  // Filtering (US4 — FR-011 through FR-014)
  const { accountId, type, from, to } = req.query;

  if (accountId) {
    results = results.filter(t => t.fromAccount === accountId || t.toAccount === accountId);
  }

  if (type) {
    results = results.filter(t => t.type === type);
  }

  if (from) {
    results = results.filter(t => t.timestamp >= from);
  }

  if (to) {
    const toEnd = to.includes('T') ? to : to + 'T23:59:59.999Z';
    results = results.filter(t => t.timestamp <= toEnd);
  }

  return res.status(200).json(results);
});

// GET /transactions/:id
router.get('/:id', (req, res) => {
  const transaction = getTransactionById(req.params.id);
  if (!transaction) {
    return res.status(404).json({ error: 'Transaction not found' });
  }
  return res.status(200).json(transaction);
});

module.exports = router;
