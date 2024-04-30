// swagger:parameters createClientAccess
type CreateClientAccessParams struct {
    // A ClientAccess object that needs to be added
    // in: body
    // required: true
    Body ClientAccess
}

// swagger:route POST /client_access clientAccess createClientAccess
// Creates a new client access.
// responses:
//   200: clientAccessResponse
// parameters:
//   - name: clientAccess
//     in: body
//     description: client access to create
//     required: true
//     schema:
//       $ref: '#/definitions/CreateClientAccessParams'

// CreateClientAccess creates a new client access.
func (s *ClientAccessService) CreateClientAccess(w http.ResponseWriter, r *http.Request) {
    // ...
}


import "github.com/swaggo/http-swagger"

// ...

func main() {
    r := chi.NewRouter()

    // ...

    r.Get("/swagger/*", httpSwagger.WrapHandler)

    // ...

    http.ListenAndServe(":8080", r)
}


// swagger:response clientAccessResponse

type ClientAccess struct {
    // ...
}


// swagger:route POST /client_access clientAccess createClientAccess
// Creates a new client access.
// responses:
//   200: clientAccessResponse

// CreateClientAccess creates a new client access.
func (s *ClientAccessService) CreateClientAccess(w http.ResponseWriter, r *http.Request) {
    // ...
}
