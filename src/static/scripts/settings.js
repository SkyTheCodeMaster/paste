const USERNAME_MIN_LENGTH = document.getElementById("username_data").getAttribute("username-min-length");
const USERNAME_MAX_LENGTH = document.getElementById("username_data").getAttribute("username-max-length");
const PASSWORD_MIN_LENGTH = document.getElementById("username_data").getAttribute("password-min-length");
const PASSWORD_MAX_LENGTH = document.getElementById("username_data").getAttribute("password-max-length");

var _password; // The password has to be stored in plaintext for changing the username. Better UX
               // than having the user enter their password when changing their username.
var user_data; // Store info from securelogin, like username
var token_delete_id; // Token ID to be deleted
var token_edit_id;

function format(_format) {
  var args = Array.prototype.slice.call(arguments, 1);
  return _format.replace(/{(\d+)}/g, function(match, number) { 
    return typeof args[number] != 'undefined'
      ? args[number] 
      : match
    ;
  });
};

function close_all_modals() {
  (document.querySelectorAll(".modal") || []).forEach( (modal) => {
    modal.classList.remove("is-active");
  })
}

function open_modal(modal_id) {
  document.getElementById(modal_id).classList.add("is-active");
}

function close_modal(modal_id) {
  document.getElementById(modal_id).classList.remove("is-active");
}

function get_cookie(name) {
  var nameEQ = name + "=";
  var ca = document.cookie.split(';');
  for(let i=0;i < ca.length;i++) {
      var c = ca[i];
      while (c.charAt(0)==' ') c = c.substring(1,c.length);
      if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
  }
  return null;
}

async function fill_user_data() {
  if (user_data == null) {
    var user_data_request = new XMLHttpRequest();
    user_data_request.open("GET","/api/internal/user/get/");
    user_data_request.send();
    user_data_request.onload = function() {
      var data = JSON.parse(user_data_request.responseText);
      user_data = data;
    }
    var waiting = true;
    while (waiting) {
      await sleep(16);
      waiting = user_data == null;
    }
  }
}

function sudo_secure_login() {
  document.getElementById("modal-sudo-invalid-password").classList.add("is-hidden");
  document.getElementById("modal-sudo-submit").classList.add("is-loading");
  document.getElementById("modal-sudo-submit").setAttribute("disabled",true);
  var password_box = document.getElementById("sudo-modal-password-input");
  var password = password_box.value;

  var insecure_token = get_cookie("token"); // We'll use this to get the username
  var username_request = new XMLHttpRequest();
  username_request.open("GET","/api/internal/user/get/");
  username_request.setRequestHeader("Authorization",insecure_token);
  username_request.send();
  username_request.onload = function() {
    var data = JSON.parse(username_request.responseText);
    user_data = data;
    var username = data.username;
    var secure_request = new XMLHttpRequest();
    secure_request.open("POST", "/api/login/");
    var params = {
      "name": username,
      "password": password,
      "secure": true
    };
    secure_request.send(JSON.stringify(params));
    secure_request.onload = function() {
      document.getElementById("modal-sudo-submit").classList.remove("is-loading");
      document.getElementById("modal-sudo-submit").removeAttribute("disabled");
      if (secure_request.status == 200) {
        close_modal("modal-sudo-mode");
        _password = password; // i'm so so sorry
        return true
      } else {
        password_box.value = "";
        document.getElementById("modal-sudo-invalid-password").classList.remove("is-hidden");
      }
    }
  }
}

// Settings change functions

function change_username() {
  document.getElementById("modal-username-button-submit").classList.add("is-loading");
  document.getElementById("modal-username-button-submit").setAttribute("disabled",true);
  var username = document.getElementById("modal-username-textbox").value;
  if (USERNAME_MAX_LENGTH < username.length) {
    document.getElementById("modal-username-button-submit").classList.remove("is-loading");
    document.getElementById("modal-username-button-submit").removeAttribute("disabled");
    create_popup("Username too long, max "+USERNAME_MAX_LENGTH);
    return;
  }
  if (USERNAME_MIN_LENGTH > username.length) {
    document.getElementById("modal-username-button-submit").classList.remove("is-loading");
    document.getElementById("modal-username-button-submit").removeAttribute("disabled");
    create_popup("Username too short, min "+USERNAME_MIN_LENGTH);
    return;
  }
  const USERN_REGEX = /[^A-Za-z0-9]/;
  if (USERN_REGEX.test(username)) {
    document.getElementById("modal-username-button-submit").classList.remove("is-loading");
    document.getElementById("modal-username-button-submit").removeAttribute("disabled");
    create_popup("Alphanumeric characters only!");
    return;
  }
  var username_request = new XMLHttpRequest();
  username_request.open("POST","/api/internal/user/edit/");
  var params = {
    "name": username,
    "password": _password // Due to how the username plays a role in hashing the password, it needs the password
                          // to generate a new hash. This way you don't get locked out of your account forever.
  };
  username_request.send(JSON.stringify(params));
  username_request.onload = function() {
    if (username_request.status == 200) {
      append_alert("Successfully edited username!");
      window.location.replace("/settings/general");
    } else {
      document.getElementById("modal-username-button-submit").classList.remove("is-loading");
      document.getElementById("modal-username-button-submit").removeAttribute("disabled");
      create_popup("HTTP" + username_request.status + ": " + username_request.responseText,true);
    }
  }
}

async function sudo_reveal_email() {
  if (get_cookie("securetoken") == null) {
    open_modal("modal-sudo-mode");
    var waiting = true;
    while (waiting) {
      await sleep(16);
      waiting = get_cookie("securetoken") == null;
    }
  }
  var secure_token = get_cookie("securetoken"); // We'll use this to get the username
  var email_request = new XMLHttpRequest();
  email_request.open("GET","/api/internal/user/get/");
  email_request.setRequestHeader("Authorization",secure_token);
  email_request.send();
  email_request.onload = function() {
    var data = JSON.parse(email_request.responseText);
    document.getElementById("user-email-box").innerText = data["email"];
  }
}

function change_email() {
  document.getElementById("modal-email-button-submit").classList.add("is-loading");
  document.getElementById("modal-email-button-submit").setAttribute("disabled",true);
  var secure_token = get_cookie("securetoken"); // We'll use this to get the email
  var old_email_invalid_warn = document.getElementById("modal-change-email-wrong-email");
  var old_email = document.getElementById("modal-change-email-old").value;
  if (old_email === "") {
    create_popup("Please enter a value for old email!",true);
  }
  var new_email = document.getElementById("modal-change-email-new").value;
  if (new_email === "") {
    create_popup("Please enter a value for new email!",true);
  }
  var email_request = new XMLHttpRequest();
  email_request.open("GET","/api/internal/user/get/");
  email_request.setRequestHeader("Authorization",secure_token);
  email_request.send();
  email_request.onload = function() {
    var data = JSON.parse(email_request.responseText);

    if (old_email != data["email"]) {
      old_email_invalid_warn.classList.remove("is-hidden");
      document.getElementById("modal-email-button-submit").classList.remove("is-loading");
      document.getElementById("modal-email-button-submit").removeAttribute("disabled");
      return
    } else {
      old_email_invalid_warn.classList.add("is-hidden");
    }

    var edit_request = new XMLHttpRequest();
    edit_request.open("POST","/api/internal/user/edit");
    var params = {
      "email": new_email
    }
    edit_request.send(JSON.stringify(params))
    edit_request.onload = function() {
      if (edit_request.status == 200) {
        append_alert("Successfully edited email!");
        window.location.replace("/settings/general");
      } else {
        document.getElementById("modal-email-button-submit").classList.remove("is-loading");
        document.getElementById("modal-email-button-submit").removeAttribute("disabled");
        create_popup("HTTP" + edit_request.status + ": " + edit_request.responseText,true);
      }
    }
  }
}

async function change_avatar() {
  document.getElementById("modal-avatar-change-button-submit").classList.add("is-loading");
  document.getElementById("modal-avatar-change-button-submit").setAttribute("disabled",true);
  var option = get_selected_avatar_option();
  var params = {};
  if (option === "url") {
    var url_value = document.getElementById("modal-avatar-url-input-box").value;
    if (url_value === "" || (!url_value.startsWith("https://") && !url_value.startsWith("http://"))) {
      create_popup("URL must start with http:// or https://!", true);
      document.getElementById("modal-avatar-change-button-submit").classList.remove("is-loading");
      document.getElementById("modal-avatar-change-button-submit").removeAttribute("disabled",false);
      return
    } else {
      params.type = 2;
      params.url = url_value;
    }
  } else if (option === "uploadfile") {
    var files = document.getElementById("modal-avatar-change-file-input").files;
    if (files.length == 0) {
      create_popup("Please select a file!", true);
      document.getElementById("modal-avatar-change-button-submit").classList.remove("is-loading");
      document.getElementById("modal-avatar-change-button-submit").removeAttribute("disabled",false);
    } else {
      // We have a file, fancy!
      var image_data = new Uint8Array(await files[0].arrayBuffer()).toString(); // This is horrible. I hate it.
      params.type = 2;
      params.bytes = image_data;
    }
  } else if (option === "gravatar") {
    params.type = 1;
  } else if (option === "default") {
    params.type = 0;
  }

  var request = new XMLHttpRequest();
  request.open("POST","/api/internal/user/setavatar");
  request.send(JSON.stringify(params));
  request.onload = function() {
    if (request.status == 200) {
      append_alert("Successfully changed avatar!");
      window.location.replace("/settings/general");
    } else {
      create_popup("HTTP" + request.status + ": " + request.responseText,true);
      document.getElementById("modal-avatar-change-button-submit").classList.remove("is-loading");
      document.getElementById("modal-avatar-change-button-submit").removeAttribute("disabled");
    }
  }
}

function download_datadump() {
  window.open("/api/internal/user/data/");
  close_modal("modal-download-datadump");
}

function refresh_token() {
  document.getElementById("modal-refresh-token-button-submit").classList.add("is-loading");
  document.getElementById("modal-refresh-token-button-submit").setAttribute("disabled",true);
  var token_request = new XMLHttpRequest();
  token_request.open("POST","/api/internal/user/refreshtoken/");
  token_request.send();
  token_request.onload = function() {
    if (token_request.status == 200) {
      document.getElementById("modal-refresh-token-button-submit").classList.remove("is-loading");
      document.getElementById("modal-refresh-token-button-submit").removeAttribute("disabled");
      append_alert("Successfully resest tokens!");
      close_modal("modal-refresh-token");
      window.location.replace("/");
    } else {
      document.getElementById("modal-refresh-token-button-submit").classList.remove("is-loading");
      document.getElementById("modal-refresh-token-button-submit").removeAttribute("disabled");
      create_popup("HTTP" + token_request.status + ": " + token_request.responseText,true);
    }
  }
}

async function change_password() {
  document.getElementById("modal-password-button-submit").classList.add("is-loading");
  document.getElementById("modal-password-button-submit").setAttribute("disabled",true);

  var old_password = document.getElementById("modal-password-textbox-old").value;
  var new_password = document.getElementById("modal-password-textbox-new").value;

  // Pre request length check
  if (new_password.length > PASSWORD_MAX_LENGTH) {
    create_popup("Password too long; max " + PASSWORD_MAX_LENGTH, true);
    document.getElementById("modal-password-button-submit").classList.remove("is-loading");
    document.getElementById("modal-password-button-submit").removeAttribute("disabled");
  }
  if (new_password.length < PASSWORD_MIN_LENGTH) {
    create_popup("Password too short; min " + PASSWORD_MIN_LENGTH, true);
    document.getElementById("modal-password-button-submit").classList.remove("is-loading");
    document.getElementById("modal-password-button-submit").removeAttribute("disabled");
  }

  await fill_user_data();

  // Check if old password is correct. Log in.
  var login_request = new XMLHttpRequest();
  login_request.open("POST","/api/login/");
  var params = {
    "password": old_password,
    "name": user_data.username,
    "secure": true
  };
  login_request.send(JSON.stringify(params));
  login_request.onload = function() {
    if (login_request.status == 200) {
      var edit_request = new XMLHttpRequest();
      edit_request.open("POST","/api/internal/user/edit/");
      var edit_params = {
        "password": new_password
      }
      edit_request.send(JSON.stringify(edit_params));
      edit_request.onload = function() {
        if (edit_request.status == 200) {
          append_alert("Successfully edited password!");
          document.getElementById("modal-password-button-submit").classList.remove("is-loading");
          document.getElementById("modal-password-button-submit").removeAttribute("disabled");
          window.location.replace("/settings/security");
        } else {
          document.getElementById("modal-password-button-submit").classList.remove("is-loading");
          document.getElementById("modal-password-button-submit").removeAttribute("disabled");
          create_popup("HTTP" + login_request.status + ": " + login_request.responseText,true);
        }
      }
    } else {
      document.getElementById("modal-password-button-submit").classList.remove("is-loading");
      document.getElementById("modal-password-button-submit").removeAttribute("disabled");
      create_popup("Old password incorrect",true);
    }
  }
}

async function delete_account() {
  document.getElementById("modal-delete-account-button-submit").classList.add("is-loading");
  document.getElementById("modal-delete-account-button-submit").setAttribute("disabled",true);

  var password = document.getElementById("modal-delete-account-textbox").value;
  var delete_pastes = document.getElementById("modal-delete-account-checkbox-delete-all-pastes").checked;
  var download_pastes = document.getElementById("modal-delete-account-checkbox-download-pastes").checked;

  if (password === "") {
    create_popup("Please enter password!",true);
    document.getElementById("modal-delete-account-button-submit").classList.remove("is-loading");
    document.getElementById("modal-delete-account-button-submit").removeAttribute("disabled");
  }

  await fill_user_data();

  // Now login to see if password is correct.
  var login_request = new XMLHttpRequest();
  login_request.open("POST","/api/login/");
  var params = {
    "password": password,
    "name": user_data.username,
    "secure": true
  };
  login_request.send(JSON.stringify(params));
  login_request.onload = function() {
    if (login_request.status == 200) {

      if (download_pastes) {
        window.open("/api/internal/user/data/");
      }
      var delete_request = new XMLHttpRequest();
      delete_request.open("DELETE","/api/internal/user/delete");
      delete_request.setRequestHeader("delete-pastes", delete_pastes)
      delete_request.send();
      delete_request.onload = function() {
        if (delete_request.status == 200) {
          append_alert("Successfully deleted account!");
          document.getElementById("modal-delete-account-button-submit").classList.remove("is-loading");
          document.getElementById("modal-delete-account-button-submit").removeAttribute("disabled");
          logout();
        } else {
          document.getElementById("modal-delete-account-button-submit").classList.remove("is-loading");
          document.getElementById("modal-delete-account-button-submit").removeAttribute("disabled");
          create_popup("HTTP" + delete_request.status + ": " + delete_request.responseText,true);
        }
      }
    } else {
      document.getElementById("modal-delete-account-button-submit").classList.remove("is-loading");
      document.getElementById("modal-delete-account-button-submit").removeAttribute("disabled");
      create_popup("Password incorrect",true);
    }
  }
}

// End settings change functions

// Token functions
async function create_token() {
  if (get_cookie("securetoken") == null) {
    open_modal("modal-sudo-mode");
    var waiting = true;
    while (waiting) {
      await sleep(16);
      waiting = get_cookie("securetoken") == null;
    }
  }

  var new_permissions = 0;
  new_permissions = set_bit(new_permissions, 0, document.getElementById("modal-create-token-create-paste").checked)
  new_permissions = set_bit(new_permissions, 1, document.getElementById("modal-create-token-edit-paste").checked)
  new_permissions = set_bit(new_permissions, 2, document.getElementById("modal-create-token-delete-paste").checked)
  new_permissions = set_bit(new_permissions, 3, document.getElementById("modal-create-token-view-private-paste").checked)

  var title = document.getElementById("modal-create-token-name").value;

  var packet = {
    "name": title,
    "perms": new_permissions
  };

  var token_create_request = new XMLHttpRequest();
  token_create_request.open("POST","/api/internal/token/create/");
  token_create_request.send(JSON.stringify(packet));
  token_create_request.onload = function() {
    if (token_create_request.status == 200) {
      append_alert("Successfully created token!");
    } else {
      append_alert(format("Couldn't create token;\nHTTP{0}: {1}",token_create_request.status,token_create_request.responseText));
    }
    window.location.reload();
  }
}

async function view_token(token_id) {
  if (get_cookie("securetoken") == null) {
    open_modal("modal-sudo-mode");
    var waiting = true;
    while (waiting) {
      await sleep(16);
      waiting = get_cookie("securetoken") == null;
    }
  }

  // Get the actual token id thing
  var token_request = new XMLHttpRequest();
  token_request.open("GET","/api/internal/token/get/?name="+token_id);
  token_request.send();
  token_request.onload = function() {
    if (token_request.status == 200) {
      var data = JSON.parse(token_request.responseText);
      var token_secure_id = data["id"];
      document.getElementById("modal-view-token-id-token-box").innerText = token_secure_id;
      document.getElementById("modal-view-token-id-token-title").innerText = format("'{0}' ID", data["title"]);

      open_modal("modal-view-token-id");
    }
  }
}

function get_bit(val, bit) {
  var mask = 1 << bit;
  return (val & mask) != 0;
}

function set_bit(val, bit, state) {
  var mask = 1 << bit;
  if (state) {
    val |= mask;
  } else {
    val &= ~mask;
  }

  return val;
}

async function edit_token(token_id) {
  if (get_cookie("securetoken") == null) {
    open_modal("modal-sudo-mode");
    var waiting = true;
    while (waiting) {
      await sleep(16);
      waiting = get_cookie("securetoken") == null;
    }
  }

  // Get the token permissions
  var token_request = new XMLHttpRequest();
  token_request.open("GET","/api/internal/token/get/?name="+token_id);
  token_request.send();
  token_request.onload = function() {
    if (token_request.status == 200) {
      var data = JSON.parse(token_request.responseText);
      var token_permissions = data["permissions"];
      var token_secure_id = data["id"];
      token_edit_id = token_secure_id;

      document.getElementById("modal-edit-token-name").value = data["title"];

      // Bit 0 is create paste
      document.getElementById("modal-edit-token-create-paste").checked = get_bit(token_permissions, 0)
      // Bit 1 is edit paste
      document.getElementById("modal-edit-token-edit-paste").checked = get_bit(token_permissions, 1)
      // Bit 2 is delete paste
      document.getElementById("modal-edit-token-delete-paste").checked = get_bit(token_permissions, 2)
      // Bit 3 is view private paste
      document.getElementById("modal-edit-token-view-private-paste").checked = get_bit(token_permissions, 3)

      open_modal("modal-edit-token");
    }
  }
}

async function edit_token_confirm() {
  if (get_cookie("securetoken") == null) {
    close_modal("modal-edit-token");
    open_modal("modal-sudo-mode");
    var waiting = true;
    while (waiting) {
      await sleep(16);
      waiting = get_cookie("securetoken") == null;
    }
  }

  var new_permissions = 0;
  new_permissions = set_bit(new_permissions, 0, document.getElementById("modal-edit-token-create-paste").checked)
  new_permissions = set_bit(new_permissions, 1, document.getElementById("modal-edit-token-edit-paste").checked)
  new_permissions = set_bit(new_permissions, 2, document.getElementById("modal-edit-token-delete-paste").checked)
  new_permissions = set_bit(new_permissions, 3, document.getElementById("modal-edit-token-view-private-paste").checked)

  var title = document.getElementById("modal-edit-token-name").value;

  var packet = {
    "id": token_edit_id,
    "name": title,
    "perms": new_permissions
  };

  var token_edit_request = new XMLHttpRequest();
  token_edit_request.open("POST","/api/internal/token/edit/");
  token_edit_request.send(JSON.stringify(packet));
  token_edit_request.onload = function() {
    if (token_edit_request.status == 200) {
      append_alert("Successfully edited token!");
    } else {
      append_alert(format("Couldn't edit token;\nHTTP{0}: {1}",token_edit_request.status,token_edit_request.responseText));
    }
    window.location.reload();
  }
}

async function delete_token(token_id) {
  if (get_cookie("securetoken") == null) {
    open_modal("modal-sudo-mode");
    var waiting = true;
    while (waiting) {
      await sleep(16);
      waiting = get_cookie("securetoken") == null;
    }
  }

  // Get the actual token id thing
  var token_request = new XMLHttpRequest();
  token_request.open("GET","/api/internal/token/get/?name="+token_id);
  token_request.send();
  token_request.onload = function() {
    if (token_request.status == 200) {
      var data = JSON.parse(token_request.responseText);

      token_delete_id = token_id;

      document.getElementById("modal-delete-token-token-title").innerText = format("Delete '{0}'?s", data["title"]);
      open_modal("modal-delete-token");
    }
  }
}

async function delete_token_confirm() {
  if (get_cookie("securetoken") == null) {
    close_modal("modal-delete-token");
    open_modal("modal-sudo-mode");
    var waiting = true;
    while (waiting) {
      await sleep(16);
      waiting = get_cookie("securetoken") == null;
    }
  }

  // Get the actual token id thing
  var token_request = new XMLHttpRequest();
  token_request.open("GET","/api/internal/token/get/?name="+token_delete_id);
  token_request.send();
  token_request.onload = function() {
    if (token_request.status == 200) {
      var data = JSON.parse(token_request.responseText);

      var token_secure_id = data["id"];

      var token_delete_request = new XMLHttpRequest();
      token_delete_request.open("DELETE","/api/internal/token/delete/");
      var params = {
        "id": token_secure_id
      };
      token_delete_request.send(JSON.stringify(params));
      token_delete_request.onload = function() {
        if (token_delete_request.status == 200) {
          append_alert("Deleted token!");
        } else {
          append_alert(format("Couldn't delete token;\nHTTP{0}: {1}",token_delete_request.status,token_delete_request.responseText));
        }
        window.location.reload();
      }
    }
  }
}

// End token functions

// Generic callback for all of the radio buttons
function modal_avatar_radio_button_callback(ele) {
  // Ele in this case is an HTTPElement thing (onclick="modal...back(this)")
  var option = get_selected_avatar_option();
  if (option === "url") {
    // Turn on the avatar input box
    document.getElementById("modal-avatar-url-input-box").removeAttribute("disabled");
  } else {
    document.getElementById("modal-avatar-url-input-box").setAttribute("disabled", true);
  }

  if (option === "uploadfile") {
    set_avatar_upload_file_input(true);
  } else {
    set_avatar_upload_file_input(false);
  }
}

function set_avatar_upload_file_input(state) {
  if (state) {
    document.getElementById("modal-avatar-change-file-super").removeAttribute("disabled");
    document.getElementById("modal-avatar-change-file-input").removeAttribute("disabled");
    document.getElementById("modal-avatar-change-file-cta").removeAttribute("disabled");
  } else {
    document.getElementById("modal-avatar-change-file-super").setAttribute("disabled",true);
    document.getElementById("modal-avatar-change-file-input").setAttribute("disabled",true);
    document.getElementById("modal-avatar-change-file-cta").setAttribute("disabled",true);
  }
}

function get_selected_avatar_option() {
  // I'm so, so sorry.
  if (document.getElementById("modal-avatar-change-radio-default").checked) {
    return "default";
  } else if (document.getElementById("modal-avatar-change-radio-gravatar").checked) {
    return "gravatar";
  } else if (document.getElementById("modal-avatar-change-radio-url").checked) {
    return "url";
  } else if (document.getElementById("modal-avatar-change-radio-upload-file").checked) {
    return "uploadfile";
  }
}

// Stuff to handle typing functions

window.addEventListener("load", function() {
  // Email modal regex checker
  try {
    var new_avatar_file_button = document.getElementById("modal-change-email-new"); // Run against the email regex.
    var new_email_invalid_warn = document.getElementById("modal-change-email-invalid-email");
    const EMAIL_REGEX = /(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])/;
    new_avatar_file_button.addEventListener("keyup", function() {
      if (!EMAIL_REGEX.test(new_avatar_file_button.value)) {
        new_email_invalid_warn.classList.remove("is-hidden");
      } else {
        new_email_invalid_warn.classList.add("is-hidden");
      }
    });
  } catch {}
  // Avatar button filename changer
  try {
    var new_avatar_file_button = document.getElementById("modal-avatar-change-file-input");
    var new_avatar_text = document.getElementById("modal-avatar-change-file-label");
    new_avatar_file_button.addEventListener("change", function() {
      var file_name = new_avatar_file_button.files[0].name;
      new_avatar_text.innerText = file_name;
    });
  } catch {}
});

// End typing functions stuff

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function sudo_open_modal(modal_id) {
  if (get_cookie("securetoken") == null) {
    open_modal("modal-sudo-mode");
    var waiting = true;
    while (waiting) {
      await sleep(16);
      waiting = get_cookie("securetoken") == null;
    }
  }
  open_modal(modal_id);
}

// Escape key closes modals
document.addEventListener("keydown", (event) => {
  if (event.code == "Escape") {
    close_all_modals();
  }
})