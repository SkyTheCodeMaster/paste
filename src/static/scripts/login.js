const email_regex = /(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])/;
const usern_regex = /[^A-Za-z0-9]/;

var usern_length_bad = true;
var usern_chars_bad = false;

function login() {
  var predicate = 
    usern_length_bad ||
    usern_chars_bad;

  if (predicate) { return; }
  // Grab the values
  var username = document.getElementById("login_username_text").value;
  var password = document.getElementById("login_password_text").value;
  var remember = document.getElementById("login_remember_me").value;
  
  // Instantiate a request
  var request = new XMLHttpRequest();
  // Set headers and URL
  request.open("POST","api/login/");
  request.setRequestHeader("Content-Type","application/json");
  var params = {
    "name": username,
    "password": password,
    "rememberme":remember,
  };
  // Send the information. The response sets a cookie which is shown to the user
  // when the view is moved to /
  request.send(JSON.stringify(params));
  request.onload = function() {
    if (request.status == 200) {
      window.location.replace("/");
    }
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

function set_check(id, state) {
  // True is a green check, false is a red X
  const X = "ph:x";
  const CHK = "mdi:check";

  var sign = document.getElementById(id);
  if (state) {
    sign.setAttribute("icon",CHK);
    sign.style.color = "green";
  } else {
    sign.setAttribute(X);
    sign.style.color = "red";
  }
}

function set_button() {
  var login_button = document.getElementById("login_button");
  var predicate = 
    !usern_length_bad && 
    !usern_chars_bad;
  login_button.disabled = !predicate;
}

function set_username_check() {
  var predicate =
    usern_chars_bad ||
    usern_length_bad;
  set_check("login_username_check",!predicate)
}

// We use this to apply an `onkeypress` listener to the username input box to check if
// it's free.
// We can also use this to run the email address against the regex.
window.addEventListener("load",function() {
  set_button();
  const USERNAME_MIN_LENGTH = document.getElementById("username_data").getAttribute("username-min-length");
  const USERNAME_MAX_LENGTH = document.getElementById("username_data").getAttribute("username-max-length");
  try {
    var username_input = document.getElementById("login_username_text");
    username_input.addEventListener("keyup", function() {
      var text = username_input.value;
      var length = text.length;
      var username_warn_reason = document.getElementById("login_username_warn_reason")
      var username_warn = document.getElementById("login_username_warn");
      if (USERNAME_MIN_LENGTH > length | length > USERNAME_MAX_LENGTH) {
        username_warn.style.display = "none";
        usern_length_bad = true;
        if (USERNAME_MIN_LENGTH > length) {
          username_warn_reason.innerHTML = format("Username is too short, minimum {0}!",USERNAME_MIN_LENGTH);
          username_warn.style.display = "block";
        } else {
          username_warn_reason.innerHTML = format("Username is too long, maximum {0}!",USERNAME_MAX_LENGTH);
          username_warn.style.display = "block";
        }
      } else {
        if (!usern_regex.test(text)) {
          username_warn.style.display = "none";
          usern_length_bad = false;
          usern_chars_bad = false;
        } else {
          username_warn_reason.innerHTML = ("Alphanumeric only!");
          username_warn.style.display = "block";
          usern_chars_bad = true;
        }
      }
      set_username_check();
      set_button();
    });
  } catch {};
});