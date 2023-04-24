const email_regex = /(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])/;

var email_bad = false;
var usern_bad = false;

function signup() {
  if (email_bad | usern_bad) { return; }
  
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
// We can also use this to run the email address against the regex.
window.onload = function() {
  const USERNAME_MIN_LENGTH = document.getElementById("username_data").getAttribute("data-min-length");
  const USERNAME_MAX_LENGTH = document.getElementById("username_data").getAttribute("data-max-length");
  try {
    var usernameInput = document.getElementById("usernameInput");
    usernameInput.addEventListener("keyup", function() {
      var text = usernameInput.value;
      var length = text.length;
      console.log(length);
      var username_length_warn = document.getElementById("username_length_bad");
      var username_exists_warn = document.getElementById("username_already_exists");
      var btn = document.getElementById("loginbtn");
      if (USERNAME_MIN_LENGTH > length | length > USERNAME_MAX_LENGTH) {
        username_exists_warn.style.display = "none";
        if (USERNAME_MIN_LENGTH > length) {
          username_length_warn.innerHTML = format("Username is too short, minimum {0}!",USERNAME_MIN_LENGTH);
          username_length_warn.style.display = "block";
        } else {
          username_length_warn.innerHTML = format("Username is too long, maximum {0}!",USERNAME_MAX_LENGTH);
          username_length_warn.style.display = "block";
        }
      } else {
        username_length_warn.style.display = "none";
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
          if (ok) {
            username_exists_warn.style.display = "none";
          } else {
            username_exists_warn.style.display = "block";
          }
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
  } catch {};
}