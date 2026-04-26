const { v4: uuidv4 } = require('uuid');

const VALID_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'CNY'];

function generateId() {
  return uuidv4();
}

function generateTimestamp() {
  return new Date().toISOString();
}

function escapeCsvField(field) {
  if (field === null || field === undefined) return '';
  const str = String(field);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

function transactionsToCsv(transactions) {
  const headers = 'id,fromAccount,toAccount,amount,currency,type,timestamp,status';
  const rows = transactions.map(t =>
    [t.id, t.fromAccount, t.toAccount, t.amount, t.currency, t.type, t.timestamp, t.status]
      .map(escapeCsvField)
      .join(',')
  );
  return [headers, ...rows].join('\n');
}

module.exports = {
  VALID_CURRENCIES,
  generateId,
  generateTimestamp,
  transactionsToCsv,
};
