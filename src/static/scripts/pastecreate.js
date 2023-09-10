var pseHighlighter;
var selected_language = "plaintext";
var paste_tag;

function create_paste(submit_button) {
  const vis_enum = {
    "public": 1,
    "unlisted": 2,
    "private": 3
  }
  // Get all of our datas
  var paste_content = document.getElementById("paste_edit_textarea").value;
  var paste_title = document.getElementById("paste_title_input").value;
  var paste_visibility = vis_enum[document.getElementById("paste_visibility_select").value.toLowerCase()];

  var packet = {
    "title": paste_title == "" ? "Untitled" : paste_title,
    "content": paste_content,
    "syntax": selected_language,
    "tags": paste_tag.items.join(","),
    "visibility": paste_visibility
  }

  console.log(packet);

  submit_button.classList.add("is-loading");
  submit_button.setAttribute("disabled",null);

  var request = new XMLHttpRequest();

  request.open("POST","/api/paste/create/");
  request.setRequestHeader("Content-Type","application/json");
  request.send(JSON.stringify(packet));
  request.onload = function() {
    if (request.status == 200) {
      append_alert("Successfully created paste!");
      window.location.replace("/" + request.responseText);
    } else if (request.status == 400) {
      // unset disabled/loading
      submit_button.removeAttribute("disabled");
      submit_button.classList.remove("is-loading");
      create_popup("Error creating paste: " + request.responseText);
    } else {
      // unset disabled/loading
      submit_button.removeAttribute("disabled");
      submit_button.classList.remove("is-loading");
      create_popup("Unknown error.");
      console.error(request.responseText);
    }
  }
}

function set_language(lang) {
  selected_language = lang.toLowerCase();
  document.getElementById("synselect-selected-language-span").innerText = title_case(lang);
  document.getElementById("synselect-full-dropdown").classList.remove("is-active");
  document.getElementById("syntax-switch").dispatchEvent(new Event("click"));
}

function title_case(str) {
  str = str.toLowerCase();
  str = str.split(' ');
  for (var i = 0; i < str.length; i++) {
    str[i] = str[i].charAt(0).toUpperCase() + str[i].slice(1);
  }
  return str.join(' ');
}

function show_dropdown() {
  var dropdown = document.getElementById("synselect-full-dropdown");
  dropdown.classList.toggle("is-active");
}

window.addEventListener("load", function() {
  paste_tag = BulmaTagsInput.attach()[0];
  shiki.getHighlighter({
    theme: "light-plus"
  }).then(highlighter => {
    pseHighlighter = highlighter;
    try {
      var languages = highlighter.getLoadedLanguages();
      languages.sort();
      var dropdown_content = document.getElementById("synselect-dropdown-languages");
      function populate_dropdown(langs) {
        dropdown_content.innerHTML = "";
        langs.sort();
        for (var lang of langs) {
          var dropdown_item_div = this.document.createElement("div");
          dropdown_item_div.classList.add("dropdown-item");
          var a = this.document.createElement("a");
          a.textContent = title_case(lang);
          const a_lang = (' ' + lang).slice(1);
          a.onclick = function() {set_language(a_lang)}
          dropdown_item_div.appendChild(a);
          dropdown_content.appendChild(dropdown_item_div)
        }
      }
      populate_dropdown(languages);

      // Handle typing text
      var searchbar = document.getElementById("synselect-dropdown-lang-search");
      searchbar.addEventListener("keyup", function() {
        var txt = searchbar.value.toLowerCase();
        var filtered_langs = languages.filter(ele => ele.includes(txt));
        populate_dropdown(filtered_langs);
      })
    } catch (error) {console.log("getting langs broke lol",error)}

    try {
      var synswitch = document.getElementById("syntax-switch");
      var textarea = document.getElementById("paste_edit_textarea");
      var output = document.getElementById("paste-output");
      output.onclick = function() { textarea.focus() }
      textarea.addEventListener("input", function() {
        // Resizing
        textarea.style.height = "auto";
        textarea.style.height = textarea.scrollHeight + "px";
        output.style.height = "auto";
        output.style.height = textarea.scrollHeight + "px";
        // Highlighting
        if (synswitch.checked) {
          textarea.style.color = "transparent";
          var highlighted_code = highlighter.codeToHtml(textarea.value, {lang: selected_language});
          output.innerHTML = highlighted_code;
        } else {
          //output.innerText = textarea.value;
          textarea.style.color = "black";
        }
      });
      synswitch.addEventListener("click", function() {
        if (synswitch.checked) {
          textarea.style.color = "transparent";
          var highlighted_code = highlighter.codeToHtml(textarea.value, {lang: selected_language});
          output.innerHTML = highlighted_code;
        } else {
          //output.innerText = textarea.value;
          textarea.style.color = "black";
        }
      });
    } catch {};
  })
});