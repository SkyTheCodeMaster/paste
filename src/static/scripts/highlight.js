const RANGE_REGEX = /(\d+)-(\d+)/;

function get_highlight_language(classes) {
  for (class_name of classes) {
    if (class_name.startsWith("lang-")) {
      return class_name.slice(5);
    }
  }
}

function generate_focus() {
  var hash = window.location.hash.substring(1);
  // We need to output a list of 
  /*
    [
      {line: x, classes:['focus']}
    ]
  */
  var lines = hash.split(",");
  var lineopts = [];
  for (var line of lines) {
    try {
      if (line.includes("-")) {
        var out = RANGE_REGEX.exec(line);
        var start = Number(out[1]);
        var end = Number(out[2]);
        for (let i=start; i<=end; i++) {
          lineopts.push({line: i, classes:["focus"]});
        }
      } else {
        lineopts.push({line: Number(line), classes:["focus"]});
      }
    } catch {};
  }
  return lineopts;
}

var main_paste_code;
var last_line_clicked;
var shift = false;
var Highlighter;

function is_in_range(number, range) {
  if (range.includes("-")) {
    var out = RANGE_REGEX.exec(range);
    var start = Number(out[1]);
    var end = Number(out[2]);
    return start <= number && number <= end;
  } else {
    return number == range;
  }
}

function is_in_hash(number_range) {
  if (toString(number_range).includes("-")) {
    var out = RANGE_REGEX.exec(number_range);
    var start = Number(out[1]);
    var end = Number(out[2]);
    for (let i=start; i<=end; i++) {
      for (ele of window.location.hash.substring(1).split(",")) {
        if (is_in_range(i, ele)) {
          return true;
        }
      }
    }
  } else {
    for (ele of window.location.hash.substring(1).split(",")) {
      if (is_in_range(number_range, ele)) {
        return true;
      }
    }
  }
  return false;
}

function add(arr, ele) {
  if (arr.indexOf(ele) == -1) {
    arr.push(ele);
  }
}

function deduplicate_hash() {
  var new_lines = [];
  var lines = window.location.hash.substring(1).split(",");
  if (lines.length == 1) {
    return;
  } 
  for (let line of lines) {
    if (line.includes("-")) {
      var out = RANGE_REGEX.exec(line);
      var start = Number(out[1]);
      var end = Number(out[2]);
      for (let i=start; i<=end; i++) {
        add(new_lines, Number(i));
      }
    } else {
      add(new_lines, Number(line));
    }
  }
  new_lines.sort((a,b) => a-b);
  remove(new_lines,0);
  final = crunch(new_lines);
  window.location.hash = final.join(",");
}

function remove(arr, ele) {
  if (arr.indexOf(ele)!=-1) {
    arr.splice(arr.indexOf(ele),1);
  }
}

function remove_from_hash(number) {
  var new_lines = [];
  var lines = window.location.hash.substring(1).split(",");
  for (let line of lines) {
    if (line.includes("-")) {
      var out = RANGE_REGEX.exec(line);
      var start = Number(out[1]);
      var end = Number(out[2]);
      for (let i=start; i<=end; i++) {
        add(new_lines, Number(i));
      }
    } else {
      add(new_lines, Number(line));
    }
  }
  remove(new_lines,number);
  final = crunch(new_lines);
  window.location.hash = final.join(",");
}

function crunch(input) {
  var output = [];
  last = input[0]-1;
  start = input[0];
  for (let current = 0; current < input.length; current++) {
    if (input[current] != last+1) {
      if (start == last) {
        output.push(start.toString());
      } else {
        output.push(start + "-" + last);
      }
      start = input[current];
    }
    last = input[current];
  }
  if (start == last) {
    output.push(start.toString());
  } else {
    output.push(start + "-" + last);
  }
  return output;
}

function line_callback(line_number) {
  var range;
  if (is_in_hash(line_number)) {
    // Remove line number and re-highlight
    remove_from_hash(line_number);
  } else {
    // Add line number and re-highlight
    if (shift && last_line_clicked != null) {
      range = last_line_clicked + "-" + line_number
    } else {
      last_line_clicked = line_number;
      range = line_number;
    }
    window.location.hash += ","+range;
  }
  deduplicate_hash();
  if (window.location.hash.substring(1) == "undefined-NaN") {
    window.location.hash = "";
  }
  rehighlight_main_code();
}

function rehighlight_main_code() {
  var block = document.getElementById("main_paste_text_block");
  const language = get_highlight_language(block.classList);
  var lineopts = generate_focus();
  const code = Highlighter.codeToHtml(main_paste_code, {lang: language, lineOptions: lineopts});
  block.innerHTML = code;
}

window.addEventListener("keydown", function(e) {
  shift = e.shiftKey;
});
window.addEventListener("keyup", function(e) {
  shift = e.shiftKey;
})

window.addEventListener("load", function() {
  shiki.
    getHighlighter({
      theme: "light-plus"
    })
    .then(highlighter => {
      Highlighter = highlighter;
      for (block of this.document.getElementsByClassName("highlight-me")) {
        if (block.getAttribute("data-is-main-paste") != null) {
          // This is the main paste
          const language = get_highlight_language(block.classList);
          var lineopts = generate_focus();
          main_paste_code = block.innerHTML;
          const code = highlighter.codeToHtml(block.innerHTML, {lang: language, lineOptions: lineopts});
          block.innerHTML = code;
        } else {
          const language = get_highlight_language(block.classList);
          const code = highlighter.codeToHtml(block.innerHTML, { lang: language });
          block.innerHTML = code;
        }
      }
    });
})