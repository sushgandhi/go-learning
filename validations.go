// pkg/store/userdetails_test.go

package store

import (
    "context"
    "net/http"
    "net/http/httptest"
    "testing"

    "github.com/gorilla/mux"
    "github.com/stretchr/testify/assert"
    "go.mongodb.org/mongo-driver/bson"
)

type MockUserStore struct {
    GetUserDetailsByIDFunc func(ctx context.Context, id string) (bson.M, error)
}

func (m *MockUserStore) GetUserDetailsByID(ctx context.Context, id string) (bson.M, error) {
    return m.GetUserDetailsByIDFunc(ctx, id)
}

func TestGetUserDetailsByID(t *testing.T) {
    mockUserStore := &MockUserStore{
        GetUserDetailsByIDFunc: func(ctx context.Context, id string) (bson.M, error) {
            return bson.M{"id": "123", "name": "Test User"}, nil
        },
    }

    r := mux.NewRouter()
    r.HandleFunc("/users/{id}", func(w http.ResponseWriter, r *http.Request) {
        vars := mux.Vars(r)
        id := vars["id"]
        user, err := mockUserStore.GetUserDetailsByID(r.Context(), id)
        if err != nil {
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(user)
    }).Methods("GET")

    req := httptest.NewRequest("GET", "/users/123", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
    assert.Contains(t, w.Body.String(), "Test User")
}
