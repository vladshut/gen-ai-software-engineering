const express = require('express');
const router = express.Router();
const { getAllTransactions } = require('../models/store');

// GET /accounts/:accountId/balance (FR-005)
router.get('/:accountId/balance', (req, res) => {
  const { accountId } = req.params;
  const transactions = getAllTransactions();
  const balances = {};

  for (const t of transactions) {
    if (t.status !== 'completed') continue;

    if (t.type === 'deposit' && t.toAccount === accountId) {
      balances[t.currency] = (balances[t.currency] || 0) + t.amount;
    } else if (t.type === 'withdrawal' && t.fromAccount === accountId) {
      balances[t.currency] = (balances[t.currency] || 0) - t.amount;
    } else if (t.type === 'transfer') {
      if (t.fromAccount === accountId) {
        balances[t.currency] = (balances[t.currency] || 0) - t.amount;
      }
      if (t.toAccount === accountId) {
        balances[t.currency] = (balances[t.currency] || 0) + t.amount;
      }
    }
  }

  return res.status(200).json({ accountId, balances });
});

// GET /accounts/:accountId/summary (FR-015)
router.get('/:accountId/summary', (req, res) => {
  const { accountId } = req.params;
  const transactions = getAllTransactions();

  let totalDeposits = 0;
  let totalWithdrawals = 0;
  let transactionCount = 0;
  let mostRecentTransaction = null;

  for (const t of transactions) {
    const involves = t.fromAccount === accountId || t.toAccount === accountId;
    if (!involves) continue;

    transactionCount++;

    if (t.type === 'deposit' && t.toAccount === accountId) {
      totalDeposits += t.amount;
    } else if (t.type === 'withdrawal' && t.fromAccount === accountId) {
      totalWithdrawals += t.amount;
    } else if (t.type === 'transfer') {
      if (t.fromAccount === accountId) totalWithdrawals += t.amount;
      if (t.toAccount === accountId) totalDeposits += t.amount;
    }

    if (!mostRecentTransaction || t.timestamp > mostRecentTransaction) {
      mostRecentTransaction = t.timestamp;
    }
  }

  return res.status(200).json({
    accountId,
    totalDeposits,
    totalWithdrawals,
    transactionCount,
    mostRecentTransaction,
  });
});

module.exports = router;
