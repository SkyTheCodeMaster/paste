function delete_paste() {
  // Get the paste ID
  var path = window.location.pathname.split("/");
  var paste_id = path.pop() || path.pop();
  
  // Instantiate a request
  var request = new XMLHttpRequest();
  // Set headers and URL
  request.open("POST","api/paste/delete/");
  request.setRequestHeader("Content-Type","application/json");
  var params = {
    "id": paste_id
  };
  // Send the information. The response sets a cookie which is shown to the user
  // when the view is moved to /
  request.send(JSON.stringify(params));
  request.onload = function() {
    if (request.status == 200) {
      append_alert("Paste deleted successfully!");
      window.location.replace("/");
    } else if (request.status == 403) {
      alert("Permission denied");
    } else if (request.status == 400) {
      alert("Bad request");
    } else if (request.status == 500) {
      alert("Internal server error");
    }
  };
}