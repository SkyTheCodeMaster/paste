const email_regex = /(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])/;

// Handle when the `login` button is clicked.
function login() {
  // Grab the values
  var username = document.getElementById("usernameInput").value;
  var password = document.getElementById("passwordInput").value;
  
  // Instantiate a request
  var request = new XMLHttpRequest();
  // Set headers and URL
  request.open("POST","api/login/");
  request.setRequestHeader("Content-Type","application/json");
  var params = {
    "name": username,
    "password": password,
  };
  // Send the information. The response sets a cookie which is shown to the user
  // when the view is moved to /
  request.send(JSON.stringify(params));
  request.onload = function() {
    window.location.replace("/");
  };
}

function signup() {

}

// We use this to apply an `onkeypress` listener to the username input box to check if
// it's free.
// We can also use this to run the email address against the regex.
window.onload = function() {
  const USERNAME_MIN_LENGTH = document.getElementById("username_data").getAttribute("data-min-length");
  const USERNAME_MAX_LENGTH = document.getElementById("username_data").getAttribute("data-max-length");
  var usernameInput = document.getElementById("usernameInput");
  usernameInput.addEventListener("keyup", function() {
    var text = usernameInput.value;
    var length = text.length;
    
    // This probably isn't the best way to do it, but who cares!
    // XMLHttpRequest for everyone!
    var request = new XMLHttpRequest()
    request.open("POST","/api/internal/user/exists");
    request.setRequestHeader("Content-Type","application/json");
    var params = {
      "name": text
    };
    request.send(JSON.stringify(params));
    request.onload = function() {
      var ok = request.responseText === "false";
      var popup = document.getElementById("username_already_exists");
      if (ok) {
        popup.style.display = "none";
      } else {
        popup.style.display = "block";
      }
    }
  });

  var emailInput = document.getElementById("emailInput");
  emailInput.addEventListener("keyup",function() {
    var text = emailInput.value;
    var popup = document.getElementById("email_invalid");
    if (!email_regex.test(text)) {
      popup.style.display = "block";
    } else {
      popup.style.display = "none";
    }
  });
}