const transactions = [];

function addTransaction(txn) {
  transactions.push(txn);
  return txn;
}

function getAllTransactions() {
  return transactions;
}

function getTransactionById(id) {
  return transactions.find(t => t.id === id) || null;
}

function clearTransactions() {
  transactions.length = 0;
}

module.exports = {
  transactions,
  addTransaction,
  getAllTransactions,
  getTransactionById,
  clearTransactions,
};
