const dynamicLink = document.getElementById('dynamic-link');
url = new URL("https://accounts.google.com/o/oauth2/v2/auth")

const params = {
    scope : [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/gmail.compose"
    ].join(" "),
    access_type : "offline",
    prompt : "consent",
    include_granted_scopes : "true",
    response_type : "code",
    redirect_uri : "https://tgrozenski.github.io/agent_email_frontend.github.io/callback.html",
    client_id : "592589126466-flt6lvus63683vern3igrska7sllq2s9.apps.googleusercontent.com"
}

Object.keys(params).forEach(key => {
    url.searchParams.append(key, params[key])
})

dynamicLink.href = url.toString()