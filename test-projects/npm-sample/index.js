const express = require('express');
const axios = require('axios');
const _ = require('lodash');

const app = express();
const port = 3000;

app.get('/', (req, res) => {
  const data = _.shuffle([1, 2, 3, 4, 5]);
  res.json({ message: 'Hello World', data });
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});
