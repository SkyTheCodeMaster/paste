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

function create_popup(reason) {
  // Create the div
  const div = document.createElement("div");

  // Create a custom ID for removing only the targetted popup.
  var id = make_id(10);
  div.id = id;

  div.classList.add("popup_box");
  // Add a header to the div
  const h1 = document.createElement("h1");
  const h1_node = document.createTextNode(reason);
  // Add the close button
  const a = document.createElement("a");
  a.onclick = function() { remove_popup(id) };
  const a_node = document.createTextNode("X");
  // Put everything together
  a.appendChild(a_node);
  h1.appendChild(h1_node);
  div.appendChild(a);
  div.appendChild(h1)
  // Add it to the HTML page.
  const body = document.body;
  body.appendChild(div);
}

function remove_popup(popup) {
  var elem = document.getElementById(popup)
  elem.parentNode.removeChild(elem);
}

window.addEventListener("load",function() {
  var data = localStorage.getItem("popup_alert");
  console.log(data);
  var arr = JSON.parse(data);
  for (const reason of arr) {
    create_popup(reason);
  }
});