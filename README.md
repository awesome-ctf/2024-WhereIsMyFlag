# ICS Exporter for Graduate Student Course Schedule

## Requirement

- Python 3.8 or later
- pip

Run `pip install -r requirements.txt` to install required components.


## Instruction

How to get the `SESSIONID`:

1. Open and login you account in web browser.
2. Open DevTools -> Network tab and then reload the page.
3. Locate the very first request after reloading or requests to domain `example.edu`.
4. Find either `Cookie: SESSIONID=` or `Set-Cookie: SESSIONID=`.
5. Copy the text after `SESSIONID=` till the first semicolon(;).


## Contribution

Pull requests and issues are always welcome.
