function get_highlight_language(classes) {
  for (class_name of classes) {
    if (class_name.startsWith("lang-")) {
      return class_name.slice(5);
    }
  }
}

window.addEventListener("load", function() {
  shiki.
    getHighlighter({
      theme: "light-plus"
    })
    .then(highlighter => {
      for (block of this.document.getElementsByClassName("highlight-me")) {
        const language = get_highlight_language(block.classList);
        const code = highlighter.codeToHtml(block.innerHTML, { lang: language });
        block.innerHTML = code;
      }
    });
})