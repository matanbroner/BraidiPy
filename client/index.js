/**
 * Testing server with Braidify JS client:
 * https://github.com/braid-org/braidjs/blob/master/braidify/braidify-client.js
 */

let http = require("http");
let braidify = require("braidify").http(http);

// Not doing anything useful, just testing incoming versions can be parsed
// braidify.get("http://localhost:8080/post/1", { subscribe: true }, (res) => {
//   res.on("error", (err) => {
//     console.error(err);
//   });
//   res.on("version", (version) => {
//     console.log(version);
//   });
// });

let patch = "\r\nContent-Length: 40";
patch += "\r\nContent-Range: json .latest_change\r\n"
patch += "\r\n{\"type\": \"title\", \"value\": \"New Title!\"}\r\n";
patches = `${patch}${patch}`

const options = {
  hostname: 'localhost',
  port: 8080,
  path: '/post/1',
  method: 'PUT',
  headers: {
    'Client': 1, // make GUID
    'Cache-Control': 'no-cache, no-transform',
    'Version': 5, // arbitrary
    'Content-Type': 'application/json',
    'Merge-Type': 'sync9',
    'Content-Length': patch.length,
    'Patches': 2 // only sending one patch
  }
}
// console.log(patch.match(/(\r?\n)(\r?\n)/))
let req = braidify.request(options, (res) => {
  res.on("error", (err) => {
    console.error(err);
  });
});
req.write(patches);
