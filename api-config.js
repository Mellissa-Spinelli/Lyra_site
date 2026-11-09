const isGithubPages = window.location.hostname === "mellissa-spinelli.github.io";
window.LYRA_CONFIG = {
  apiBaseUrl: isGithubPages ? "https://lyra-site-api-mellissa-spinelli.onrender.com" : "",
};
