(async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const codeElement = document.getElementById('code');
    const statusElement = document.getElementById('status');

    if (code) {
        if (codeElement) {
            codeElement.textContent = code;
        }
        if (statusElement) {
            statusElement.textContent = 'Successfully received code. Exchanging for token...';
        }
        console.log("Here is the code", code);

        // TODO: Send the code to the backend to exchange for an access token.
        /*
        try {
            const response = await fetch('YOUR_BACKEND_ENDPOINT', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ code }),
            });

            if (response.ok) {
                const data = await response.json();
                // Handle successful authentication, e.g., store token, redirect
                if (statusElement) {
                    statusElement.textContent = 'Authentication successful!';
                }
                console.log('Token exchange successful', data);
            } else {
                // Handle error
                if (statusElement) {
                    statusElement.textContent = 'Token exchange failed.';
                }
                console.error('Token exchange failed');
            }
        } catch (error) {
            if (statusElement) {
                statusElement.textContent = 'An error occurred.';
            }
            console.error('Error during token exchange:', error);
        }
        */
    } else {
        if (statusElement) {
            statusElement.textContent = 'No authorization code found in URL.';
        }
    }
})();
