type MockMongoUserStore struct {
    CountUsersFunc     func(ctx context.Context) (int64, error)
    AddUserDetailsFunc func(ctx context.Context, user User) error
}

func (m *MockMongoUserStore) CountUsers(ctx context.Context) (int64, error) {
    return m.CountUsersFunc(ctx)
}

func (m *MockMongoUserStore) AddUserDetails(ctx context.Context, user User) error {
    return m.AddUserDetailsFunc(ctx, user)
}

func TestAddUserDetails(t *testing.T) {
    mockStore := &MockMongoUserStore{
        CountUsersFunc: func(ctx context.Context) (int64, error) {
            return 0, nil
        },
        AddUserDetailsFunc: func(ctx context.Context, user User) error {
            return nil
        },
    }

    userService := NewUserService(mockStore)
    user := User{ID: "123", Name: "Test User"}
    userJson, _ := json.Marshal(user)
    req := httptest.NewRequest("POST", "/users", bytes.NewBuffer(userJson))
    req.Header.Set("Content-Type", "application/json")
    w := httptest.NewRecorder()

    _, err := userService.AddUserDetails(w, req)
    if err != nil {
        t.Fatalf("expected no error, got %v", err)
    }

    assert.Equal(t, http.StatusOK, w.Code)
}
