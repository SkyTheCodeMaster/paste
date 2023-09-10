function logout() {
  document.cookie = "token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
  window.location.replace("/");
}

function make_id(length) {
  let result = '';
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (var i=0; i<length; i++) {
    result += characters.charAt(Math.floor(Math.random() * characters.length));
  }
  return result;
}
function append_alert(reason) {
  // Get current alerts
  var data = JSON.parse(localStorage.getItem("popup_alert"));
  // Append our alert
  data.push(reason);
  // Write the alerts back
  localStorage.setItem("popup_alert",JSON.stringify(data));
}

function create_popup(reason) {
  // Create the div
  const div = document.createElement("div");

  // Create a custom ID for removing only the targetted popup.
  var id = make_id(10);
  div.id = id;

  div.style.position = "fixed";
  div.style.top =    "25px";
  div.style.right =  "40%";
  div.style.width =  "20%";
  div.style.zIndex = "100";

  const notification = document.createElement("div")
  notification.classList.add("notification");
  notification.classList.add("is-primary");
  // Add a header to the div
  const text_node = document.createTextNode(reason);
  // Add the close button
  const button = document.createElement("button");
  button.classList.add("delete")
  button.onclick = function() { remove_popup(id,reason) };
  // Put everything together
  notification.appendChild(button);
  notification.appendChild(text_node)
  div.appendChild(notification);
  // Add it to the HTML page.
  const body = document.body;
  body.appendChild(div);
}

function remove_popup(popup,reason) {
  var elem = document.getElementById(popup)
  elem.parentNode.removeChild(elem);
  // Now remove the popup from local storage
  var data = JSON.parse(localStorage.getItem("popup_alert"));
  var idx = data.indexOf(reason);
  if (idx !== -1) { data.splice(idx, 1) }
  localStorage.setItem("popup_alert",JSON.stringify(data));
}

window.addEventListener("load",function() {
  if (!this.localStorage.getItem("popup_alert")) {
    this.localStorage.setItem("popup_alert","[]")
  }
  if (this.window.document.documentMode) {
    create_popup("Internet explorer is not a supported browser for this website.");
  }
  var data = localStorage.getItem("popup_alert");
  var arr = JSON.parse(data);
  for (const reason of arr) {
    create_popup(reason);
  }
});

document.addEventListener("keydown", function(e) {
  if (e.key === 's' && e.ctrlKey) {
    e.preventDefault();
  }
});