// services/userdetail.go

package services

import (
    "github.com/go-chi/chi"
    "github.com/yourusername/yourproject/store"
    "net/http"
    "encoding/json"
)

// User represents the structure of your user data
type User struct {
    ID   string `json:"id"`
    Name string `json:"name"`
    // other fields...
}

func GetUserDetailsByIDHandler(w http.ResponseWriter, r *http.Request) {
    userStore, ok := r.Context().Value("userStore").(store.MongoDB)
    if !ok {
        http.Error(w, "userStore not available", http.StatusInternalServerError)
        return
    }

    id := chi.URLParam(r, "id")
    user, err := userStore.GetUserByID(id)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    json.NewEncoder(w).Encode(user)
}

func CreateUserHandler(w http.ResponseWriter, r *http.Request) {
    userStore, ok := r.Context().Value("userStore").(store.MongoDB)
    if !ok {
        http.Error(w, "userStore not available", http.StatusInternalServerError)
        return
    }

    user, ok := r.Context().Value("user").(User)
    if !ok {
        http.Error(w, "invalid user data", http.StatusInternalServerError)
        return
    }

    id, err := userStore.CreateUser(user)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    json.NewEncoder(w).Encode(map[string]string{"id": id})
}
