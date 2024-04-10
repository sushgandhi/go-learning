// pkg/services/userdetail_test.go

package services

import (
    "context"
    "net/http"
    "net/http/httptest"
    "testing"
    "github.com/go-chi/chi"
    "github.com/yourusername/yourproject/pkg/store"
    "go.mongodb.org/mongo-driver/bson"
)

func TestUserDetailService_GetUserByID(t *testing.T) {
    mockStore := &store.MockUserDetailStore{
        GetUsersByIDFunc: func(ctx context.Context, id string) ([]bson.M, error) {
            return []bson.M{{"id": "123", "name": "Test User"}}, nil
        },
    }

    userService := NewUserDetailService(mockStore)

    r := chi.NewRouter()
    r.Get("/{id}", userService.GetUserByID)

    req := httptest.NewRequest("GET", "/123", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)

    if w.Code != http.StatusOK {
        t.Fatalf("expected status OK, got %v", w.Code)
    }

    // Add more assertions as needed
}

// Add tests for GetUser and AddUser



// pkg/store/userdetailstore_test.go

package store

import (
    "context"
    "testing"
    "go.mongodb.org/mongo-driver/bson"
)

func TestUserDetailStore_GetUsersByID(t *testing.T) {
    mockMongoStore := &MockMongoStore{
        FindFunc: func(ctx context.Context, filter bson.M) ([]bson.M, error) {
            return []bson.M{{"id": "123", "name": "Test User"}}, nil
        },
    }

    userDetailStore := NewUserDetailStore(mockMongoStore)

    users, err := userDetailStore.GetUsersByID(context.Background(), "123")
    if err != nil {
        t.Fatalf("expected nil error, got %v", err)
    }

    expectedUsers := []bson.M{{"id": "123", "name": "Test User"}}
    if !reflect.DeepEqual(users, expectedUsers) {
        t.Fatalf("expected %v, got %v", expectedUsers, users)
    }
}

// Add tests for other methods


// pkg/store/userdetailstore_test.go

package store

import (
    "context"
    "go.mongodb.org/mongo-driver/bson"
)

type MockUserDetailStore struct {
    GetUsersByIDFunc func(ctx context.Context, id string) ([]bson.M, error)
    // Add other methods as needed
}

func (m *MockUserDetailStore) GetUsersByID(ctx context.Context, id string) ([]bson.M, error) {
    return m.GetUsersByIDFunc(ctx, id)
}

// Implement other methods as needed

// pkg/store/userdetailstore_test.go

package store

import (
    "context"
    "testing"
    "go.mongodb.org/mongo-driver/bson"
)

func TestUserDetailStore_GetUsersByID(t *testing.T) {
    mockMongoStore := &MockMongoStore{
        FindFunc: func(ctx context.Context, filter bson.M) ([]bson.M, error) {
            return []bson.M{{"id": "123", "name": "Test User"}}, nil
        },
    }

    userDetailStore := NewUserDetailStore(mockMongoStore)

    users, err := userDetailStore.GetUsersByID(context.Background(), "123")
    if err != nil {
        t.Fatalf("expected nil error, got %v", err)
    }

    expectedUsers := []bson.M{{"id": "123", "name": "Test User"}}
    if !reflect.DeepEqual(users, expectedUsers) {
        t.Fatalf("expected %v, got %v", expectedUsers, users)
    }
}

// Add tests for other methods




// pkg/store/mongostore.go

package store

import (
    "context"
    "go.mongodb.org/mongo-driver/bson"
)

type MongoStore interface {
    FindOne(ctx context.Context, filter bson.M) (bson.M, error)
    // Add more methods as needed
}


// pkg/store/mongostore.go

type MongoStoreImpl struct {
    collection *mongo.Collection
}

func (s *MongoStoreImpl) FindOne(ctx context.Context, filter bson.M) (bson.M, error) {
    var result bson.M
    err := s.collection.FindOne(ctx, filter).Decode(&result)
    return result, err
}

func NewMongoStore(db *mongo.Database, collectionName string) MongoStore {
    return &MongoStoreImpl{collection: db.Collection(collectionName)}
}



// pkg/store/mongostore_test.go

package store

import (
    "context"
    "go.mongodb.org/mongo-driver/bson"
    "testing"
)

type MockMongoStore struct {
    FindOneFunc func(ctx context.Context, filter bson.M) (bson.M, error)
}

func (m *MockMongoStore) FindOne(ctx context.Context, filter bson.M) (bson.M, error) {
    return m.FindOneFunc(ctx, filter)
}

func TestUserDetailStore_GetUser(t *testing.T) {
    mockStore := &MockMongoStore{
        FindOneFunc: func(ctx context.Context, filter bson.M) (bson.M, error) {
            return bson.M{"id": "123", "name": "Test User"}, nil
        },
    }

    userDetailStore := &UserDetailStore{store: mockStore}

    // Now you can call userDetailStore.GetUser and it will use the mock implementation of FindOne
}


// pkg/store/mongostore_test.go

package store

import (
    "context"
    "go.mongodb.org/mongo-driver/bson"
    "go.mongodb.org/mongo-driver/mongo"
)

type MockMongoStore struct {
    FindFunc func(ctx context.Context, filter bson.M) ([]bson.M, error)
    // Add other methods as needed
}

func (m *MockMongoStore) Find(ctx context.Context, filter bson.M) ([]bson.M, error) {
    return m.FindFunc(ctx, filter)
}

// Implement other methods as needed



