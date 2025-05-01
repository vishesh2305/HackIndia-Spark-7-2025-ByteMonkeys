module.exports = {
  solidity: "0.8.19", // Or your Solidity version
  networks: {
    ganache: {
      url: "http://localhost:7545", // Ganache RPC server address
      accounts: {
        mnemonic: "test test test test test test test test test test test test", // Or the one Ganache provides
        count: 10,
      },
    },
  },
};