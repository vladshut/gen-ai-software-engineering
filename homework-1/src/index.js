const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

const transactionsRouter = require('./routes/transactions');
const accountsRouter = require('./routes/accounts');

app.use('/transactions', transactionsRouter);
app.use('/accounts', accountsRouter);

if (require.main === module) {
  app.listen(port, () => {
    console.log(`Banking Transactions API running on port ${port}`);
  });
}

module.exports = app;
