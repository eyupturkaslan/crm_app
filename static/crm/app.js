// Theme toggle + Ctrl/Cmd+K global search focus.
document.addEventListener("click", function (e) {
  if (!e.target.closest("[data-theme-toggle]")) return;
  var dark = document.documentElement.classList.toggle("dark");
  try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch (err) {}
});

document.addEventListener("keydown", function (e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    var input = document.getElementById("global-search");
    if (input) { e.preventDefault(); input.focus(); }
  }
  if (e.key === "Escape") {
    var results = document.getElementById("search-results");
    if (results) results.innerHTML = "";
  }
});
