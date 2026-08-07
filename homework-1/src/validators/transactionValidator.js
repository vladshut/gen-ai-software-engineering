const VALID_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'CNY'];
const VALID_TYPES = ['deposit', 'withdrawal', 'transfer'];
const ACCOUNT_REGEX = /^ACC-[A-Za-z0-9]{5}$/;

function validateTransaction(body) {
  const errors = [];

  // Amount validation
  if (body.amount === undefined || body.amount === null) {
    errors.push({ field: 'amount', message: 'Amount is required' });
  } else if (typeof body.amount !== 'number' || isNaN(body.amount)) {
    errors.push({ field: 'amount', message: 'Amount must be a positive number' });
  } else if (body.amount <= 0) {
    errors.push({ field: 'amount', message: 'Amount must be a positive number' });
  } else {
    const decimalParts = body.amount.toString().split('.');
    if (decimalParts[1] && decimalParts[1].length > 2) {
      errors.push({ field: 'amount', message: 'Amount must have at most 2 decimal places' });
    }
  }

  // Type validation
  if (!body.type) {
    errors.push({ field: 'type', message: 'Type is required' });
  } else if (!VALID_TYPES.includes(body.type)) {
    errors.push({ field: 'type', message: 'Type must be deposit, withdrawal, or transfer' });
  }

  // Currency validation
  if (!body.currency) {
    errors.push({ field: 'currency', message: 'Currency is required' });
  } else if (!VALID_CURRENCIES.includes(body.currency)) {
    errors.push({ field: 'currency', message: 'Invalid currency code' });
  }

  // Account validation based on transaction type
  const type = body.type;

  if (type === 'withdrawal' || type === 'transfer') {
    if (!body.fromAccount) {
      errors.push({ field: 'fromAccount', message: 'fromAccount is required for this transaction type' });
    } else if (!ACCOUNT_REGEX.test(body.fromAccount)) {
      errors.push({ field: 'fromAccount', message: 'Account number must follow ACC-XXXXX format' });
    }
  } else if (body.fromAccount && !ACCOUNT_REGEX.test(body.fromAccount)) {
    errors.push({ field: 'fromAccount', message: 'Account number must follow ACC-XXXXX format' });
  }

  if (type === 'deposit' || type === 'transfer') {
    if (!body.toAccount) {
      errors.push({ field: 'toAccount', message: 'toAccount is required for this transaction type' });
    } else if (!ACCOUNT_REGEX.test(body.toAccount)) {
      errors.push({ field: 'toAccount', message: 'Account number must follow ACC-XXXXX format' });
    }
  } else if (body.toAccount && !ACCOUNT_REGEX.test(body.toAccount)) {
    errors.push({ field: 'toAccount', message: 'Account number must follow ACC-XXXXX format' });
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

module.exports = { validateTransaction };
