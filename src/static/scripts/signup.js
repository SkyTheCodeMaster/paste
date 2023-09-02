const email_regex = /(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])/;
const usern_regex = /[^A-Za-z0-9]/;

var email_bad = true;
var usern_length_bad = false;
var usern_exists_bad = false;
var usern_chars_bad = false;
var password_bad = false;

function signup() {
  var predicate = 
    usern_exists_bad ||
    usern_length_bad ||
    usern_chars_bad  ||
    email_bad        ||
    password_bad;

  if (predicate) { return; }

  var username   = document.getElementById("signup_username_text").value;
  var email      = document.getElementById("signup_email_text").value;
  var password   = document.getElementById("signup_password_text").value;
  var rememberme = document.getElementById("signup_remember_me").value;

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

function set_check(id, state) {
  // True is a green check, false is a red X
  const X = "fa-x";
  const CHK = "fa-check";

  var sign = document.getElementById(id);
  if (state) {
    sign.classList.remove(X);
    sign.classList.add(CHK)
    sign.style.color = "green";
  } else {
    sign.classList.remove(CHK);
    sign.classList.add(X)
    sign.style.color = "red";
  }
}

function set_button() {
  var signup_button = document.getElementById("signup_button");
  var predicate = 
    !usern_exists_bad && 
    !usern_length_bad && 
    !usern_chars_bad  &&
    !email_bad        &&
    !password_bad;
  signup_button.disabled = !predicate;
}

function set_username_check() {
  var predicate =
    usern_exists_bad ||
    usern_chars_bad  ||
    usern_length_bad;
  set_check("signup_username_check",!predicate)
}

// We use this to apply an `onkeypress` listener to the username input box to check if
// it's free.
// We can also use this to run the email address against the regex.
window.addEventListener("load",function() {
  set_button();
  const USERNAME_MIN_LENGTH = document.getElementById("username_data").getAttribute("username-min-length");
  const USERNAME_MAX_LENGTH = document.getElementById("username_data").getAttribute("username-max-length");
  const PASSWORD_MIN_LENGTH = document.getElementById("username_data").getAttribute("password-min-length");
  const PASSWORD_MAX_LENGTH = document.getElementById("username_data").getAttribute("password-max-length");
  try {
    var username_input = document.getElementById("signup_username_text");
    username_input.addEventListener("keyup", function() {
      var text = username_input.value;
      var length = text.length;
      var username_warn_reason = document.getElementById("signup_username_warn_reason")
      var username_warn = document.getElementById("signup_username_warn");
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
    username_input.addEventListener("blur", function() {
      // This probably isn't the best way to do it, but who cares!
      // XMLHttpRequest for everyone!
      var text = username_input.value;
      var username_warn_reason = document.getElementById("signup_username_warn_reason")
      var username_warn = document.getElementById("signup_username_warn");
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
          username_warn.style.display = "none";
        } else {
          username_warn.style.display = "block";
          username_warn_reason.innerHTML = "Username already exists!"
        }
        usern_exists_bad = !ok;
        set_username_check();
        set_button();
      }
    });

    var email_input = document.getElementById("signup_email_text");
    email_input.addEventListener("keyup",function() {
      var text = email_input.value;
      var popup = document.getElementById("signup_email_warn");
      if (!email_regex.test(text)) {
        email_bad = true;
        set_check("signup_email_check",false);
        popup.style.display = "block";
      } else {
        email_bad = false;
        set_check("signup_email_check",true);
        popup.style.display = "none";
      }
      set_button();
    });

    var password_input = document.getElementById("signup_password_text");
    password_input.addEventListener("keyup", function() {
      var text = password_input.value;
      var length = text.length;
      var password_warn_reason = document.getElementById("signup_password_warn_reason")
      var password_warn = document.getElementById("signup_password_warn");
      if (PASSWORD_MIN_LENGTH > length | length > PASSWORD_MAX_LENGTH) {
        password_warn.style.display = "none";
        password_bad = true;
        set_check("signup_password_check",false)
        if (PASSWORD_MIN_LENGTH > length) {
          password_warn_reason.innerHTML = format("Password is too short, minimum {0}!",PASSWORD_MIN_LENGTH);
          password_warn.style.display = "block";
        } else {
          password_warn_reason.innerHTML = format("Password is too long, maximum {0}!",PASSWORD_MAX_LENGTH);
          password_warn.style.display = "block";
        }
      } else {
        password_bad = false;
        set_check("signup_password_check",true);
        password_warn.style.display = "none";
      }
      set_button();
    })
  } catch {};
});