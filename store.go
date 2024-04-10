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

