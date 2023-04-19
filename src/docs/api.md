# Public API Documentation
The API is authenticated with either a hash of the account password, or an API token.  
Using API tokens is highly recommended, because if one is compromised, you can delete the token, and it is removed.  

Using a password as an API token is possible, to do so, the password must be hashed with SHA256 10 times, like:  
```lua
local function hash(username,passwd)
  local hash = ""
  for i=1,10 do
    hash=sha256.digest(username..passwd..hash)
  end
  return hash
end
```
Or:  
```py
def hash(passwd: str, username: str) -> str:
  "Returns a SHA256 hash of the password."
  hash = sha256(f"{username}{passwd}".encode()).hexdigest()
  for i in range(9):
    hash = sha256(f"{username}{passwd}{hash}".encode()).hexdigest()
  return hash
```  
This token will have full privileges for the account, so be careful with it!  
(This includes changing email address, changing password, etc)  

Other tokens can be created in [the token page](), and have less privileges.  
The available privileges are:  
- Create paste  
- Edit paste (Name, visibility, content)  
- Delete paste  
- View private pastes  

The API endpoint is `/api/`, all of the API functions will be available here.  
All authenticated endpoints must have the `Authorization` header passed, with a content of `"Bearer <token>"`  

# POST Method  
All data submitted in POST methods must be encoded as JSON.  

# API Endpoints  
## GET `/api/paste/get/<paste id>`:  
  
  This endpoint will get the JSON information of a paste.  
  If the paste is private, it will return a 401.  
  If the paste does not exist, it will return a 404.  

  To get a private paste, you must pass an authorization header in the form of:  
  `Authorization = "Bearer (token)"`  
  If the token does not have the `View private pastes` intent, a 401 will be returned.  

## GET `/api/paste/raw/get/<paste id>`:  

  This endpoint will get the raw content of a paste.  
  If the paste is private, it will return a 401.  
  If the paste does not exist, it will return a 404.  
    
  To get a private paste, you must pass an authorization header in the form of:  
  `Authorization = "Bearer (token)`  
  If the token does not have the `View private pastes` intent, a 401 will be returned.  

## GET `/api/paste/search/`  
  
  This endpoint searches for a *public* paste, using query tags.  
  The valid queries are:  
  - `title: string` A title to search for, case insensitive.  
  - `creator: string` The user that created the paste.  
  - `results: int` The maximum limit of results shown. Default is 50, max is 250.  
  - `page: int` The page number of results, for paginating past the maximum limit.  
  These tags are optional, and both can be passed.

  If the `Authorization` header is present, and the token has the `View private pastes` intent,  
  private pastes belonging to the owner of the token will be returned too.

  This returns a list of JSON objects for each paste.  

## POST `/api/paste/create/` - **Authenticated**
  
  This endpoint creates a paste as the user account of the token owner.  
  Post data:  
  - `title`: string The title of the paste.  
  - `content`: string The content of the paste.
  - `visibility`: integer=2 The visibility of the paste. `1` is public, `2` is unlisted, `3` is private. Default is unlisted.  
  This will return 200 andthe paste id if successful.  
  This will return a 401 if no authentication is passed, or is invalid.  
  This will return a 400 if a required field is not passed.  

## POST `/api/paste/edit/` - **Authenticated**  
  
  This endpoint will edit a paste. All data except id is optional.  
  Post data:
  - `id`: string The ID of the paste to edit.  
  - `title`: string The new title of the paste.  
  - `content`: string The content of the paste.  
  - `visibility`: integer The new visibility of the paste.  

  This will return a 200 if successful.  
  This will return a 401 if no authentication is passed, or is invalid, or the user account does not own the paste.  
  This will return a 404 if the paste is not found.  

## DELETE `/api/paste/delete/<paste id>` - **Authenticated**  

  This endpoint will delete a paste given in the path.  

  This will return a 200 if successful.  
  This will return a 401 if no authentication is passed, or is invalid, or the user account does not own the paste.  
  This will return a 404 if the paste is not found.  