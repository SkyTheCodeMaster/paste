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


function _clone(paste_id) {
  var request = new XMLHttpRequest();
  request.open("GET","/api/paste/get/"+paste_id);
  request.send();
  request.onload = function() {
    console.log(request.status)
    if (request.status == 200) {
      var paste_object = json.parse(request.responseText)
      var request = new XMLHttpRequest();
      params = {
        content: paste_object.content,
        title: paste_object.title,
        visibility: paste_object.visibility,
        syntax: paste_object.syntax
      };
      request.open("POST","/api/paste/create");
      request.send(JSON.stringify(params));
      request.onload = function() {
        if (request.status == 200) {
          append_alert("Successfully cloned paste!");
          window.location.replace("/"+request.responseText);
        } else {
          append_alert("Failed to create paste!");
          window.location.replace("/");
        }
      }
    } else {
      alert("Failed to get paste metadata!");
    }
  }
}

function clone() {
  // Get the paste ID
  var path = window.location.pathname.split("/");
  var paste_id = path.pop() || path.pop();

  _clone(paste_id);
}