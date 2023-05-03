const email_regex = /(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])/;

var email_bad = false;
var usern_bad = false;

function signup() {
  if (email_bad | usern_bad) { return; }
  
  var username = document.getElementById("usernameInput").value;
  var email = document.getElementById("emailInput").value;
  var password = document.getElementById("passwordInput").value;
  var rememberme = document.getElementById("rememberme").value;

  var packet = {
    "name":username,
    "email":email,
    "password":password,
    "rememberme":rememberme,
  };

  var request = new XMLHttpRequest();
  request.open("POST","api/internal/user/create/");
  request.setRequestHeader("Content-Type","application/json");
  request.send(JSON.stringify(packet));
  request.onload = function() {
    if (request.status == 200) {
      window.location.replace("/");
    }
  }
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
window.addEventListener("load",function() {
  const USERNAME_MIN_LENGTH = document.getElementById("username_data").getAttribute("data-min-length");
  const USERNAME_MAX_LENGTH = document.getElementById("username_data").getAttribute("data-max-length");
  var login_button = document.getElementById("loginbtn");
  try {
    var usernameInput = document.getElementById("usernameInput");
    usernameInput.addEventListener("keyup", function() {
      var text = usernameInput.value;
      var length = text.length;
      console.log(length);
      var username_length_warn = document.getElementById("username_length_bad");
      var username_exists_warn = document.getElementById("username_already_exists");
      if (USERNAME_MIN_LENGTH > length | length > USERNAME_MAX_LENGTH) {
        username_exists_warn.style.display = "none";
        usern_bad = true;
        login_button.classList.add("disabled");
        if (USERNAME_MIN_LENGTH > length) {
          username_length_warn.innerHTML = format("Username is too short, minimum {0}!",USERNAME_MIN_LENGTH);
          username_length_warn.style.display = "block";
        } else {
          username_length_warn.innerHTML = format("Username is too long, maximum {0}!",USERNAME_MAX_LENGTH);
          username_length_warn.style.display = "block";
        }
      } else {
        username_length_warn.style.display = "none";
        usern_bad = false;
        if (!email_bad) {
          login_button.classList.remove("disabled");
        }
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
        email_bad = true;
        login_button.classList.add("disabled")
        popup.style.display = "block";
      } else {
        email_bad = false;
        popup.style.display = "none";
        if (!usern_bad) {
          login_button.classList.remove("disabled");
        }
      }
    });
  } catch {};
});