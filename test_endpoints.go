package store

import (
    "bytes"
    "context"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"

    "github.com/go-chi/chi"
    "github.com/stretchr/testify/assert"
    "go.mongodb.org/mongo-driver/bson"
)

type User struct {
    ID   string `json:"id"`
    Name string `json:"name"`
}

type MockUserStore struct {
    GetUserDetailsFunc     func(ctx context.Context) ([]User, error)
    GetUserDetailsByIDFunc func(ctx context.Context, id string) (User, error)
    AddUserDetailsFunc     func(ctx context.Context, user User) error
    UpdateUserDetailsFunc  func(ctx context.Context, id string, user User) error
    DeleteUserDetailsFunc  func(ctx context.Context, id string) error
}

func (m *MockUserStore) GetUserDetails(ctx context.Context) ([]User, error) {
    return m.GetUserDetailsFunc(ctx)
}

func (m *MockUserStore) GetUserDetailsByID(ctx context.Context, id string) (User, error) {
    return m.GetUserDetailsByIDFunc(ctx, id)
}

func (m *MockUserStore) AddUserDetails(ctx context.Context, user User) error {
    return m.AddUserDetailsFunc(ctx, user)
}

func (m *MockUserStore) UpdateUserDetails(ctx context.Context, id string, user User) error {
    return m.UpdateUserDetailsFunc(ctx, id, user)
}

func (m *MockUserStore) DeleteUserDetails(ctx context.Context, id string) error {
    return m.DeleteUserDetailsFunc(ctx, id)
}

func TestGetUserDetails(t *testing.T) {
    mockUserStore := &MockUserStore{
        GetUserDetailsFunc: func(ctx context.Context) ([]User, error) {
            return []User{{ID: "123", Name: "Test User"}}, nil
        },
    }

    r := chi.NewRouter()
    r.Get("/users", func(w http.ResponseWriter, r *http.Request) {
        users, err := mockUserStore.GetUserDetails(r.Context())
        if err != nil {
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(users)
    })

    req := httptest.NewRequest("GET", "/users", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
    assert.Contains(t, w.Body.String(), "Test User")
}

func TestAddUserDetails(t *testing.T) {
    mockUserStore := &MockUserStore{
        AddUserDetailsFunc: func(ctx context.Context, user User) error {
            return nil
        },
    }

    r := chi.NewRouter()
    r.Post("/users", func(w http.ResponseWriter, r *http.Request) {
        var user User
        err := json.NewDecoder(r.Body).Decode(&user)
        if err != nil {
            http.Error(w, err.Error(), http.StatusBadRequest)
            return
        }

        err = mockUserStore.AddUserDetails(r.Context(), user)
        if err != nil {
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }

        w.WriteHeader(http.StatusCreated)
    })

    user := User{ID: "123", Name: "Test User"}
    userJson, _ := json.Marshal(user)
    req := httptest.NewRequest("POST", "/users", bytes.NewBuffer(userJson))
    req.Header.Set("Content-Type", "application/json")
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)

    assert.Equal(t, http.StatusCreated, w.Code)
}

func TestUpdateUserDetails(t *testing.T) {
    mockUserStore := &MockUserStore{
        UpdateUserDetailsFunc: func(ctx context.Context, id string, user User) error {
            return nil
        },
    }

    r := chi.NewRouter()
    r.Patch("/users/{id}", func(w http.ResponseWriter, r *http.Request) {
        id := chi.URLParam(r, "id")
        var user User
        err := json.NewDecoder(r.Body).Decode(&user)
        if err != nil {
            http.Error(w, err.Error(), http.StatusBadRequest)
            return
        }

        err = mockUserStore.UpdateUserDetails(r.Context(), id, user)
        if err != nil {
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }

        w.WriteHeader(http.StatusOK)
    })

    user := User{ID: "123", Name: "Test User Updated"}
    userJson, _ := json.Marshal(user)
    req := httptest.NewRequest("PATCH", "/users/123", bytes.NewBuffer(userJson))
    req.Header.Set("Content-Type", "application/json")
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
}

func TestDeleteUserDetails(t *testing.T) {
    mockUserStore := &MockUserStore{
        DeleteUserDetailsFunc: func(ctx context.Context, id string) error {
            return nil
        },
    }

    r := chi.NewRouter()
    r.Delete("/users/{id}", func(w http.ResponseWriter, r *http.Request) {
        id := chi.URLParam(r, "id")
        err := mockUserStore.DeleteUserDetails(r.Context(), id)
        if err != nil {
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }

        w.WriteHeader(http.StatusOK)
    })

    req := httptest.NewRequest("DELETE", "/users/123", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
}
