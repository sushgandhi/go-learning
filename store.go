// Assuming this is your interface
type UserDetailsStore interface {
    FindUserByID(ctx context.Context, id string) (store.User, error)
    // Other methods...
}

// Your MockUserDetails should implement UserDetailsStore
type MockUserDetails struct {
    FindUserByIDFunc func(ctx context.Context, id string) (store.User, error)
    // Other function fields...
}

func (m *MockUserDetails) FindUserByID(ctx context.Context, id string) (store.User, error) {
    return m.FindUserByIDFunc(ctx, id)
}

// Other methods...

// Now you can use MockUserDetails in place of mongodbstore in your tests
func TestGetUserByID(t *testing.T) {
    mockUserDetails := &MockUserDetails{
        FindUserByIDFunc: func(ctx context.Context, id string) (store.User, error) {
            return store.User{ID: "123", Name: "Test User"}, nil
        },
    }

    // GetUserByID should accept a UserDetailsStore, so you can pass in mockUserDetails
    r := chi.NewRouter()
    r.Get("/{userID}", GetUserByID(mockUserDetails))

    // ...
}
// pkg/store/mongodb_test.go

package store

import (
    "context"
    "go.mongodb.org/mongo-driver/mongo"
)

type MockCollection struct {
    FindOneFunc func(ctx context.Context, filter interface{}) *mongo.SingleResult
    // Add other methods as needed
}

func (m *MockCollection) FindOne(ctx context.Context, filter interface{}) *mongo.SingleResult {
    return m.FindOneFunc(ctx, filter)
}

// Implement other methods as needed


// pkg/store/mongodb_test.go

package store

import (
    "context"
)

type MockSingleResult struct {
    DecodeFunc func(val interface{}) error
}

func (m *MockSingleResult) Decode(val interface{}) error {
    return m.DecodeFunc(val)
}


// pkg/store/mongodb_test.go

package store

import (
    "context"
    "go.mongodb.org/mongo-driver/bson"
)

type MockMongoStore struct {
    FindOneFunc func(ctx context.Context, filter interface{}) SingleResult
    // Add other methods as needed
}

func (m *MockMongoStore) FindOne(ctx context.Context, filter interface{}) SingleResult {
    return m.FindOneFunc(ctx, filter)
}

// Implement other methods as needed

// pkg/store/userdetailstore_test.go

package store

import (
    "context"
)

type MockUserDetailStore struct {
    GetUsersByIDFunc func(ctx context.Context, id string) error
    // Add other methods as needed
}

func (m *MockUserDetailStore) GetUsersByID(ctx context.Context, id string) error {
    return m.GetUsersByIDFunc(ctx, id)
}

// Implement other methods as needed

