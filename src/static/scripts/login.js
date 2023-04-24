var bad_input_username = false;

// Handle when the `login` button is clicked.
function login() {
  if (bad_input) { return; }
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

function format(_format) {
  var args = Array.prototype.slice.call(arguments, 1);
  return _format.replace(/{(\d+)}/g, function(match, number) { 
    return typeof args[number] != 'undefined'
      ? args[number] 
      : match
    ;
  });
};

// We use this to apply an `onkeypress` listener to the username input box to check if
// it's free.
window.onload = function() {
  const USERNAME_MIN_LENGTH = document.getElementById("username_data").getAttribute("data-min-length");
  const USERNAME_MAX_LENGTH = document.getElementById("username_data").getAttribute("data-max-length");
  try {
    var usernameInput = document.getElementById("usernameInput");
    usernameInput.addEventListener("keyup", function() {
      var text = usernameInput.value;
      var length = text.length;
      console.log(length);
      var warn = document.getElementById("username_length_bad");
      var button = document.getElementById("loginbtn");
      console.log(USERNAME_MIN_LENGTH > length, length > USERNAME_MAX_LENGTH)
      if (USERNAME_MIN_LENGTH > length | length > USERNAME_MAX_LENGTH) {
        button.classList.add("disabled");
        bad_input_username = true;
        if (USERNAME_MIN_LENGTH > length) {
          warn.innerHTML = format("Username is too short, minimum {0}!",USERNAME_MIN_LENGTH);
          warn.style.display = "block";
        } else {
          warn.innerHTML = format("Username is too long, maximum {0}!",USERNAME_MAX_LENGTH);
          warn.style.display = "block";
        }
      } else {
        warn.style.display = "none";
        bad_input_username = false;
        button.classList.remove("disabled");
      }
    });
  } catch {};
}