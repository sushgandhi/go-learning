func TestUpdateUserDetails(t *testing.T) {
    mockUserStore := &MockUserStore{
        UpdateUserDetailsFunc: func(ctx context.Context, id string, user map[string]interface{}) (*mongo.UpdateResult, error) {
            return &mongo.UpdateResult{MatchedCount: 1, ModifiedCount: 1}, nil
        },
    }

    r := chi.NewRouter()
    r.Patch("/users/{id}", func(w http.ResponseWriter, r *http.Request) {
        var user map[string]interface{}
        err := json.NewDecoder(r.Body).Decode(&user)
        if err != nil {
            http.Error(w, err.Error(), http.StatusBadRequest)
            return
        }

        id := chi.URLParam(r, "id")
        result, err := mockUserStore.UpdateUserDetails(r.Context(), id, user)
        if err != nil {
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }

        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(result)
    })

    user := map[string]interface{}{"name": "Updated User"}
    userJson, _ := json.Marshal(user)
    req := httptest.NewRequest("PATCH", "/users/123", bytes.NewBuffer(userJson))
    req.Header.Set("Content-Type", "application/json")
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
    assert.Contains(t, w.Body.String(), "1")
}
