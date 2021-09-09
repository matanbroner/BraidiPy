/**
 * Testing server with Braidify JS client:
 * https://github.com/braid-org/braidjs/blob/master/braidify/braidify-client.js
 */

let http = require("http");
let braidify = require("braidify").http(http);

// Not doing anything useful, just testing incoming versions can be parsed
braidify.get("http://localhost:8080/post/1", { subscribe: true }, (res) => {
  res.on("error", (err) => {
    console.error(err);
  });
  res.on("version", (version) => {
    console.log(version);
  });
});
