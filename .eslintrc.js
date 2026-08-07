module.exports = {
  plugins: ["import"],
  rules: {
    "import/no-restricted-paths": [
      "error",
      {
        zones: [
          {
            target: "./apps/observatory",
            from: "./legacy_demo",
            message: "PROVENANCE VIOLATION: Observatory cannot import from legacy_demo."
          },
          {
            target: "./services",
            from: "./legacy_demo",
            message: "PROVENANCE VIOLATION: Services cannot import from legacy_demo."
          }
        ]
      }
    ]
  }
};
