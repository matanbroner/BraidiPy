/**
 * Testing server with Braidify JS client:
 * https://github.com/braid-org/braidjs/blob/master/braidify/braidify-client.js
 */

let http = require("http");
let braidify = require("braidify").http(http);

function test_get() {
  braidify.get("http://localhost:8080/post/1", { subscribe: "keep-alive" }, (res) => {
    res.on("error", (err) => {
      console.error(err);
    });
    res.on("version", (version) => {
      console.log(version);
    });
  });
}

function test_put() {
  let patch = "\r\nContent-Length: 40";
  patch += "\r\nContent-Range: json .latest_change\r\n";
  patch += '\r\n{"type": "title", "value": "New Title!"}\r\n';
  patches = `${patch}${patch}`;

  const options = {
    hostname: "localhost",
    port: 8080,
    path: "/post/1",
    method: "PUT",
    headers: {
      Client: 1, // make GUID
      "Cache-Control": "no-cache, no-transform",
      Version: 5, // arbitrary
      "Content-Type": "application/json",
      "Merge-Type": "sync9",
      "Content-Length": patches.length,
      Patches: 2, // only sending one patch
    },
  };
  let req = braidify.request(options, (res) => {
    res.on("error", (err) => {
      console.error(err);
    });
  });
  req.write(patches);
}

let cmd = process.argv[2];
if (cmd === "get") {
  test_get();
}
else if (cmd === "put") {
  test_put();
}
else {
  console.log("Usage: node index.js <get|put>");
}