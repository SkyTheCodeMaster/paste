// Handle when the `login` button is clicked.
function login() {
  var username = document.getElementById("usernameInput").value;
  var password = document.getElementById("passwordInput").value;
  
  var request = new XMLHttpRequest();
  request.open("POST","api/login/");
  request.setRequestHeader("Content-Type","application/json");
  var params = {
    "name": username,
    "password": password,
  };
  request.send(JSON.stringify(params));
  request.onload = function() {};
}